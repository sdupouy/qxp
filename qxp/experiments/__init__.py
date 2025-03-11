import os
from qxp.utils.config import get_project_dir


project_dir = get_project_dir()
experiments_dir = os.path.join(project_dir, 'experiments')  # Path to the user's experiments directory
if experiments_dir not in __path__:
    __path__.append(experiments_dir)  # Add it to __path__ if it’s not already there
