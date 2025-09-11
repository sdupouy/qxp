import os
import sys
import shutil
import importlib.resources as pkg_resources
import argparse
from pathlib import Path
import django
from django.core.management import call_command

import qxp
from qxp.utils.backup import BackupManager, BackupState


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

def backup():
    p = argparse.ArgumentParser(
        description="qxp backup"
    )
    p.add_argument("--data_dir", help="Path to your data directory")
    p.add_argument("--backup_dir", help="Path to your backup directory")
    pd.add_argument("--trust-stats", action="store_true", help="Skip checksums when size/mtime match")
    p.add_argument("--dry-run", action="store_true", help="Run diff without actually copying files")
    args = p.parse_args()

    bm = BackupManager(args.data_dir, args.backup_dir)  # None will resolve to default paths in config

    try:
        if args.dry_run:
            bm.diff(trust_stats=args.trust_stats)
        else:
            bm.backup(trust_stats=args.trust_stats)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(2)
