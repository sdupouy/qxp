import os
import shutil
import importlib.resources as pkg_resources
import qxp


def create_project():
    import sys
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
