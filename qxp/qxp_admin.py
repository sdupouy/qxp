import os
import sys
import shutil
import subprocess
import importlib.resources as pkg_resources
import argparse
import django
from django.core.management import call_command

import qxp
from qxp.utils.backup import BackupManager, BACKUP_LOG_NAME
from qxp.config import BACKUP_PATH


def migrate_project(qxp_project_dir):
    """Apply Django migrations."""
    os.environ['QXP_PROJECT_DIR'] = qxp_project_dir
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qxp.measurement_db.settings")
    django.setup()  # Initialize Django before running management commands
    call_command("migrate")


def create_project():
    if len(sys.argv) != 2:
        print("Usage: qxp-create-project projectname")
        return

    project_name = sys.argv[1]
    target_dir = os.path.join(os.getcwd(), project_name)  # Create project in current directory

    if os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' already exists.")
        return

    template_dir = str(pkg_resources.files(qxp) / "project_template")
    shutil.copytree(template_dir, target_dir)
    print(f"Project '{project_name}' created successfully at {target_dir}.")
    migrate_project(target_dir)


def start_webpanel():
    """Run the Django server."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qxp.measurement_db.settings")
    django.setup()  # Initialize Django before running management commands
    call_command("runserver")


def _open_in_pager(filepath: str):
    """ Open a file in the system pager. """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    # Use user's preferred pager if defined
    pager = os.environ.get("PAGER")

    if pager:
        subprocess.run([pager, filepath])
        return

    # Fallback logic
    if os.name == "nt":  # Windows
        subprocess.run(["more", filepath], shell=True)
    else:  # Unix
        pager = shutil.which("less") or shutil.which("more")
        if pager:
            subprocess.run([pager, filepath])
        else:
            # Final fallback: just print
            with open(filepath) as f:
                print(f.read())


def backup():
    p = argparse.ArgumentParser(
        description="qxp backup"
    )
    p.add_argument("--data_dir", help="Path to your data directory")
    p.add_argument("--backup_dir", help="Path to your backup directory")
    p.add_argument("--dry-run", action="store_true", help="Run diff without actually copying files")
    p.add_argument("--trust-stats", action="store_true", help="Skip checksums when size/mtime match")
    p.add_argument("--skip-validation", action="store_true", help="Don't ask for user validation")
    p.add_argument("--show-log", action="store_true", help="Show the backup log (won't run anything)")
    args = p.parse_args()

    if args.show_log:
        if args.backup_dir:
            log_path = args.backup_dir
        elif BACKUP_PATH is not None:
            log_path = os.path.join(BACKUP_PATH, BACKUP_LOG_NAME)
        else:
            print("Error: Must specify a backup directory")
            sys.exit(1)
        _open_in_pager(log_path)

    else:
        bm = BackupManager(args.data_dir, args.backup_dir)  # None will resolve to default paths in config

        try:
            if args.dry_run:
                bm.diff(trust_stats=args.trust_stats, skip_validation=args.skip_validation)
            else:
                bm.backup(trust_stats=args.trust_stats, skip_validation=args.skip_validation)
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(2)
