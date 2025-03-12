import os
import sys
import shutil
import importlib.resources as pkg_resources

import qxp
import django
from django.core.management import call_command


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
