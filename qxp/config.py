""" Global configuration file.
Here are defined the configuration parameters that will be used by the experiment classes.
Per-experiment (local) configurations are placed within the user directory at EXPERIMENT_CONFIG_PATH.
"""

from pathlib import Path
import os
import django

from qxp.utils.config import get_project_dir, load_experiment_config_module


# required to run Django in a jupyter notebook [https://docs.djangoproject.com/en/5.1/topics/async/#async-safety]
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
# setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qxp.measurement_db.settings')
django.setup()  # should only run once

# Global configuration
QXP_PROJECT_DIR = Path(get_project_dir())  # The qxp project directory
EXPERIMENT_CONFIG_PATH = QXP_PROJECT_DIR / 'qxp_config.py'  # Path to the user experiment config
DATA_DIRNAME = 'data'
DEBUG_SCRIPTS_DIRNAME = 'debug_scripts'
FIGURES_DIRNAME = 'figures'
TIMESTAMP_FORMAT = "%d-%m-%Y_%Hh%Mm%S"
TIME_ZONE = 'Europe/Paris'
STORAGE_PATH = QXP_PROJECT_DIR / 'storage'

# Load experiment configuration from the local module.
experiment_config = load_experiment_config_module(EXPERIMENT_CONFIG_PATH)  # The user configuration module

# These are extracted from the user config
CURRENT_CHIP = getattr(experiment_config, 'FORCE_CURRENT_CHIP', None)  # If not specified, fall back to the chip of the latest cooldown
MPLSTYLE_PATH = experiment_config.MPLSTYLE_PATH
EXP_CONFIG = experiment_config.EXP_CONFIG
OPX_CONNECTION = experiment_config.OPX_CONNECTION
INSTRUMENTS_CONFIG = experiment_config.INSTRUMENTS_CONFIG
get_qua_config = experiment_config.get_qua_config  # Function that returns the QUA config
ALLOW_DELETE_EXPRUN = getattr(experiment_config, 'ALLOW_DELETE_EXPRUN', True)  # Whether to allow to delete experiment runs from the webpanel
BACKUP_PATH = getattr(experiment_config, 'BACKUP_PATH', None)
