import json
from pathlib import Path
from datetime import datetime
import xxhash
import sqlite3
from pathspec import PathSpec
from enum import Enum, auto
import shutil
from tqdm import tqdm
import sys

from qxp.config import QXP_PROJECT_DIR, BACKUP_PATH


CHECKSUM_DB_NAME = '.backup_checksums.sqlite3'
DELETED_DIR_NAME = '.backup_deleted'
BACKUPIGNORE_NAME = '.backupignore'
BACKUP_LOG_NAME = '.backups.log'
UNREGISTERED_BACKUPS = '.unregistered_backups'


def compute_checksum(path, chunk_size=8192):
    """Compute xxhash64 checksum of the given file."""
    h = xxhash.xxh64()
    with open(path, 'rb') as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


class BackupState(Enum):
    """ State of the backup: initialized, diff done, backup complete. """
    INIT = auto()
    DIFFED = auto()
    BACKED_UP = auto()


class BackupManager:
    """
    A class to manage data backups.

    Its core method is 'backup'. It should be called only once: a new instance of this class should be created at each
    backup. The only exception is the 'backup_single_file' method, which allows for backing up a single file (e.g. when
    a measurement has finished and autobackup is enabled).
    A database is retrieved or created to store the checksums of the files to backup. The files checksums are compared
    to determine if they have changed. If so, the database is updated and the backup is updated according to the
    differences. The number of created/modified/deleted files or directories is logged on the backup location.
    No file is deleted: rather, they are moved to the '.backup_deleted' directory at the root of the backup location.
    """
    def __init__(self, root_data_path=None, root_backup_path=None):
        """
        Initialize the backup manager.
        Args:
            root_data_path: Path to the data directory.
            root_backup_path: Path to the backup directory.
        """
        # allowing to pass defaults using None makes it easier for commandline scripts with optional arguments
        if root_data_path is None:
            root_data_path = QXP_PROJECT_DIR
        if root_backup_path is None:
            if BACKUP_PATH is None:
                print("[!] Error: No backup path was specified. Aborting backup.")
                sys.exit(1)
            root_backup_path = BACKUP_PATH
        self.root_data_path = Path(root_data_path).resolve()
        self.root_backup_path = Path(root_backup_path).resolve()
        self.backupignore_spec = self._load_backupignore()
        self.unregistered_files = {}  # already copied but checksum not in database (recent single-file backups)
        self.added_files = {}
        self.deleted_files = []
        self.deleted_dirs = []
        self.updated_files = {}
        self.num_untouched_files = 0
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.n_elements_to_copy = 0
        self.state = BackupState.INIT

    def _load_backupignore(self):
        """Load the backupignore file, and return a PathSpec instance."""
        backupignore_path = self.root_data_path / BACKUPIGNORE_NAME
        if not backupignore_path.exists():
            print(f'[!] No {BACKUPIGNORE_NAME} file found. Backing up everything.')
            return PathSpec.from_lines("gitwildmatch", [])
        with open(backupignore_path) as f:
            lines = f.readlines()
        return PathSpec.from_lines("gitwildmatch", lines)

    def _should_ignore(self, path):
        """
        Return whether a file should be ignored (according to the backupignore file,
        or because it is the checksum database).
        """
        rel_path = path.relative_to(self.root_data_path).as_posix()
        if path.is_dir():
            rel_path += '/'  # otherwise .backupignore doesn't recognize it as a directory
        checksum_db_path = self.root_data_path / CHECKSUM_DB_NAME
        return (
            self.backupignore_spec.match_file(rel_path)
            or path == checksum_db_path
            or path == checksum_db_path.with_suffix('.sqlite3-wal')  # tmp file created when the database is open
            or path == checksum_db_path.with_suffix('.sqlite3-shm')  # tmp file created when the database is open
        )

    def _only_in_backup(self, path):
        """Return whether a file is expected to be found on the backup but not the local storage."""
        deleted_path = self.root_backup_path / DELETED_DIR_NAME  # the "deleted" directory
        log_path = self.root_backup_path / BACKUP_LOG_NAME  # the log file
        return path == deleted_path or path == log_path

    def _build_stored_checksum_db(self, path):
        """Build a sqlite database to store the checksums of the backed up files, as well as some metadata."""
        with sqlite3.connect(path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_checksums (
                    path TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    size INTEGER,
                    mtime INTEGER
                )
                """)
            conn.commit()

    def _file_checksum_changed(self, path, checksum_db_conn):
        """
        Check whether the file's checksum is still the one stored in the database.
        Args:
            path (pathlib.Path): Path to the file.
            checksum_db_conn (sqlite3.Connection): Database connection object.
        Returns:
            The new checksum if it has changed or wasn't stored, or None if it matches the one stored in the database.
        """
        checksum = compute_checksum(path)
        key = path.relative_to(self.root_data_path).as_posix()
        cur = checksum_db_conn.execute(
            "SELECT checksum FROM file_checksums WHERE path = ?",
            (key,)
        )
        row = cur.fetchone()
        if row is None or checksum != row[0]:
            return checksum

    def _file_stats_changed(self, path, checksum_db_conn):
        """
        Check whether the file's size or last modification time changed.
        Args:
            path (pathlib.Path): Path to the file.
            checksum_db_conn (sqlite3.Connection): Database connection object.
        Returns:
            The new (size, mtime) tuple if it changed, or None if it matches the one stored in the database.
        """
        key = path.relative_to(self.root_data_path).as_posix()
        cur = checksum_db_conn.execute(
            "SELECT size, mtime FROM file_checksums WHERE path = ?",
            (key,)
        )
        row = cur.fetchone()
        size = row[0]
        mtime = row[1]
        file_stats = path.stat()
        if size != file_stats.st_size or mtime != int(file_stats.st_mtime):
            return file_stats.st_size, int(file_stats.st_mtime)

    def _walk_through_files(self, root_path, ignore_func=None):
        """
        Recursively yield files within root_path if it is a directory, or directly root_path if it is a file.
        Args:
            root_path (pathlib.Path): Path of the root file.
            ignore_func (callable, or None): A function that takes a file path and returns whether it should be ignored.
                If None, no files are ignored. The root_path is never ignored.
        """
        if root_path.is_file():
            yield root_path
        elif root_path.is_dir():
            for path in root_path.iterdir():
                if ignore_func is None or not ignore_func(path):
                    yield from self._walk_through_files(path, ignore_func=ignore_func)

    def _add_or_update_files_to_db(self, files, checksum_db_conn):
        """
        Add or update a batch of files in the checksum database.
        Args:
            files (dict): A dictionary of files to add or update, of the form
                {
                'path/to/file': {
                    'checksum': ...,
                    'size': ...,
                    'mtime': ...,
                    },
                ...
                }
            checksum_db_conn (sqlite3.Connection): Database connection object.
        """
        if files:
            checksum_db_conn.executemany("""
                INSERT INTO file_checksums (path, checksum, size, mtime)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    checksum = excluded.checksum,
                    size = excluded.size,
                    mtime = excluded.mtime
                """,
                [(path, meta["checksum"], meta["size"], meta["mtime"])
                for path, meta in files.items()]
            )

    def _delete_files_and_dirs_in_db(self, deleted_files, deleted_dirs, checksum_db_conn):
        # Delete individual files (exact match)
        if deleted_files:
            checksum_db_conn.executemany(
                "DELETE FROM file_checksums WHERE path = ?",
                [(f,) for f in deleted_files]
            )
        # Delete everything under each deleted directory
        if deleted_dirs:
            checksum_db_conn.executemany(
                "DELETE FROM file_checksums WHERE path LIKE ?",
                [(d.rstrip('/') + '/%',) for d in deleted_dirs]
            )

    def _log_unregistered_backups_registration_summary(self, log_path):
        """Log a summary of the unregistered backups registration in a file at log_path."""
        summary = [
            f"[{self.timestamp}] UNREGISTERED BACKUPS REGISTRATION\n",
            f"  Registered: {len(self.unregistered_files)} files\n",
            "-----\n"
        ]
        registered_lines = [f"  + {path}\n" for path in self.unregistered_files.keys()]
        log_lines = summary + registered_lines + ["\n"]

        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.writelines(log_lines)

    def _log_backup_summary(self, log_path, trust_stats):
        """Log a summary of the backup in a file at log_path."""
        if self.state != BackupState.BACKED_UP:
            raise RuntimeError("_log_backup_summary() can only be called once the backup completed")


        header = f"[{self.timestamp}] BACKUP RUN\n"
        header += f"Compare mode: {'trust stats' if trust_stats else 'checksum'}\n"
        summary = [
            f"  Added: {len(self.added_files)} files\n",
            f"  Updated: {len(self.updated_files)} files\n",
            f"  Deleted files: {len(self.deleted_files)}\n",
            f"  Deleted dirs: {len(self.deleted_dirs)}\n",
            f"  Untouched files: {self.num_untouched_files}\n",
            "-----\n"
        ]
        added_lines = [f"  + {path}\n" for path in self.added_files.keys()]
        updated_lines = [f"  ~ {path}\n" for path in self.updated_files.keys()]
        deleted_lines = [f"  - {path}\n" for path in self.deleted_files + self.deleted_dirs]
        log_lines = [header] + summary + added_lines + updated_lines + deleted_lines + ["\n"]

        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.writelines(log_lines)

    def _register_unregistered_backups(self, checksum_db_conn):
        """ Update the database with the backups waiting to be registered (i.e. recent single-file backups). """
        # Track unregistered files
        unregistered_backups_dir = self.root_backup_path / UNREGISTERED_BACKUPS
        if unregistered_backups_dir.is_dir():
            for unregistered_backup in unregistered_backups_dir.iterdir():
                with open(unregistered_backup, 'r') as f:
                    record = json.load(f)
                self.unregistered_files[record['key']] = {
                    'checksum': record['checksum'],
                    'size': record['size'],
                    'mtime': record['mtime']
                }

        if self.unregistered_files:
            # Update the database and log
            self._add_or_update_files_to_db(self.unregistered_files, checksum_db_conn)
            self._log_unregistered_backups_registration_summary(self.root_backup_path / BACKUP_LOG_NAME)

            # Delete '.unregistered_backups'
            shutil.rmtree(unregistered_backups_dir)

    def diff(self, trust_stats=False, skip_validation=False, leave_db_locally=False):
        """
        Walk through the files and find out which ones were added, updated and deleted.
        This method also first registers unregistered backups (i.e. recent single-file backups).
        Args:
            trust_stats (bool): Whether to trust file stats (size and last modified) to determine that a file was
                untouched.
            skip_validation (bool): Whether to skip user validation that we should proceed.
            leave_db_locally (bool): Whether to leave the database at the temporary local location.
        """
        def _diff(data_path, backup_path, checksum_db_conn):
            """Recursive helper for diff."""
            data_childs = set([p.name for p in data_path.iterdir() if not self._should_ignore(p)])
            backup_childs = set([p.name for p in backup_path.iterdir() if not self._only_in_backup(p)])

            new = data_childs - backup_childs  # elements that were added since last backup
            deleted = backup_childs - data_childs  # elements that were deleted since last backup
            common = data_childs & backup_childs  # elements common to both storage and backup

            # Add new files to added_files
            for name in new:
                path = data_path / name
                for p in self._walk_through_files(path, ignore_func=self._should_ignore):
                    checksum = compute_checksum(p)
                    key = p.relative_to(self.root_data_path).as_posix()
                    file_stat = p.stat()
                    self.added_files[key] = {
                        'checksum': checksum,
                        'size': file_stat.st_size,
                        'mtime': int(file_stat.st_mtime)
                    }

            # Add deleted files/dirs to deleted_files/dirs
            for name in deleted:
                path = backup_path / name
                key = path.relative_to(self.root_backup_path).as_posix()
                if path.is_file():
                    self.deleted_files.append(key)
                elif path.is_dir():
                    self.deleted_dirs.append(key)

            # Add modified files to updated_files
            for name in common:
                data_child = data_path / name
                backup_child = backup_path / name
                if data_child.is_dir() and backup_child.is_dir():
                    # Recurse in the case of a common directory
                    _diff(data_child, backup_child, checksum_db_conn)
                elif data_child.is_file() and backup_child.is_file():
                    if trust_stats:
                        # Skip checksum computation if the stats haven't changed
                        if not self._file_stats_changed(data_child, checksum_db_conn):
                            self.num_untouched_files += 1
                            continue
                    if new_checksum := self._file_checksum_changed(data_child, checksum_db_conn):
                        key = data_child.relative_to(self.root_data_path).as_posix()
                        file_stat = data_child.stat()
                        self.updated_files[key] = {
                            'checksum': new_checksum,
                            'size': file_stat.st_size,
                            'mtime': int(file_stat.st_mtime)
                        }
                    else:
                        self.num_untouched_files += 1
                else:
                    print(f"[!] Warning: {data_child} and {backup_child} aren't both a file or both a directory. Skipping.")

        if not skip_validation:
            rep = input(f"[!] Initiating backup from {self.root_data_path} to {self.root_backup_path}. Continue? (y/n) ")
            if rep != 'y':
                sys.exit(0)

        if self.state != BackupState.INIT:
            raise RuntimeError("diff() can only be called once, at start")

        # Move the stored checksum database locally if it exists on the backup server, or create it
        checksum_db_path = self.root_backup_path / CHECKSUM_DB_NAME
        tmp_checksum_db_path = self.root_data_path / CHECKSUM_DB_NAME
        if checksum_db_path.exists():
            shutil.move(checksum_db_path, self.root_data_path)
        else:
            self._build_stored_checksum_db(tmp_checksum_db_path)

        # Do the diff recursively, after registering unregistered backups
        with sqlite3.connect(tmp_checksum_db_path) as checksum_db_conn:
            checksum_db_conn.execute("PRAGMA journal_mode=WAL")  # should increase performance
            self._register_unregistered_backups(checksum_db_conn)
            _diff(self.root_data_path, self.root_backup_path, checksum_db_conn)
        checksum_db_conn.close()  # needs to be closed explicitely to work

        # Move the checksum database back to the backup location
        if not leave_db_locally:
            shutil.move(tmp_checksum_db_path, checksum_db_path)

        # Display the diff result
        print("Diff since last backup:")
        print(f"  Files registered: {len(self.unregistered_files)}")
        print(f"  Files added:      {len(self.added_files)}")
        print(f"  Files deleted:    {len(self.deleted_files)}")
        print(f"  Dirs deleted:     {len(self.deleted_dirs)}")
        print(f"  Files updated:    {len(self.updated_files)}")
        print(f"  Files untouched:  {self.num_untouched_files}")
        self.n_elements_to_copy = len(self.added_files) + len(self.updated_files)

        # Mark BackupManager state as diffed
        self.state = BackupState.DIFFED

    def backup(self, trust_stats=False, skip_validation=False):
        """
        Back up the data files. This is the core method of BackupManager.
        Args:
            trust_stats: Whether to trust file stats (size and last modified) to determine that a file was untouched.
            skip_validation (bool): Whether to skip user validation that we should proceed.
        """
        # Do the diff if it wasn't done before.
        if self.state == BackupState.INIT:
            self.diff(trust_stats=trust_stats, skip_validation=skip_validation, leave_db_locally=True)
        elif self.state == BackupState.BACKED_UP:
            raise RuntimeError("backup() can only be called once")

        pbar = tqdm(total=self.n_elements_to_copy)  # progress bar

        # Copy new files
        for rel_path in self.added_files:
            dest_path = self.root_backup_path / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root_data_path / rel_path, dest_path)
            pbar.update(1)

        # Move deleted dirs to .backup_deleted
        for rel_path in self.deleted_dirs:
            trash_path = self.root_backup_path / DELETED_DIR_NAME / self.timestamp / rel_path
            trash_path.mkdir(parents=True)  # path should not exist yet
            shutil.move(self.root_backup_path / rel_path, trash_path)

        # Move deleted orphaned files to .backup_deleted
        for rel_path in self.deleted_files:
            trash_path = (self.root_backup_path / DELETED_DIR_NAME / self.timestamp / rel_path).parent
            trash_path.mkdir(parents=True, exist_ok=True)
            shutil.move(self.root_backup_path / rel_path, trash_path)

        # Update relevant files
        for rel_path in self.updated_files:
            shutil.copy2(self.root_data_path / rel_path, self.root_backup_path / rel_path)
            pbar.update(1)

        pbar.close()

        # Move the stored checksum database locally if it is not already there
        checksum_db_path = self.root_backup_path / CHECKSUM_DB_NAME
        tmp_checksum_db_path = self.root_data_path / CHECKSUM_DB_NAME
        if not tmp_checksum_db_path.exists():
            shutil.move(checksum_db_path, self.root_data_path)

        # Update the database
        with sqlite3.connect(tmp_checksum_db_path) as checksum_db_conn:
            checksum_db_conn.execute("PRAGMA journal_mode=WAL")  # should increase performance
            self._add_or_update_files_to_db(self.added_files | self.updated_files, checksum_db_conn)
            self._delete_files_and_dirs_in_db(self.deleted_files, self.deleted_dirs, checksum_db_conn)
        checksum_db_conn.close()  # needs to be closed explicitely to work

        # Move the checksum database back to the backup location
        shutil.move(tmp_checksum_db_path, checksum_db_path)

        # Update state
        self.state = BackupState.BACKED_UP

        # Log the backup summary
        self._log_backup_summary(self.root_backup_path / BACKUP_LOG_NAME, trust_stats)
        print("[+] Backup complete.")


def backup_single_file(path, root_data_path=QXP_PROJECT_DIR, root_backup_path=BACKUP_PATH):
    """
    Back up a single file. The database isn't updated, but a JSON file is created in '.unregistered_backups'
    for later batch update of the database.
    Args:
        path: Path of the file to back up.
        root_data_path: Path to the data directory.
        root_backup_path: Path to the backup directory.
    """
    if root_backup_path is None:
        print("[!] Error: No backup path was specified. Aborting backup.")
        return

    if not path.is_relative_to(root_data_path):
        print(f"[!] Error: {path} is not relative to {root_data_path} and will not be backed up.")
        return

    # Add file hash to a file in '.unregistered_backups'
    unregistered_backups_dir = root_backup_path / UNREGISTERED_BACKUPS
    unregistered_backups_dir.mkdir(parents=True, exist_ok=True)
    key = path.relative_to(root_data_path).as_posix()
    file_stat = path.stat()
    record = {
        'key': key,
        'checksum': compute_checksum(path),
        'size': file_stat.st_size,
        'mtime': int(file_stat.st_mtime)
    }
    filename = xxhash.xxh64(key).hexdigest() + '.json'
    with open(unregistered_backups_dir / filename, 'w') as f:
        json.dump(record, f)  # this isn't an atomic operation, but it shouldn't be a problem in our use-case

    # Copy file to backup location
    shutil.copy2(path, root_backup_path / key)
