""" Global configuration file.
Here are defined the configuration parameters that will be used by the experiment classes.
Per-experiment (local) configurations can be placed within the corresponding experiment directory.
The local configuration to be used is specified in the EXPERIMENT_CONFIG_PATH constant.
"""

from pathlib import Path

from qxp.utils.config import load_experiment_config_module


BASE_DIR = Path(__file__).resolve().parent
EXPERIMENT_CONFIG_PATH = BASE_DIR / 'experiments/autocat/config/experiment_config.py'
DATA_DIRNAME = 'data'
DEBUG_SCRIPTS_DIRNAME = 'debug_scripts'
FIGURES_DIRNAME = 'figures'
TIMESTAMP_FORMAT = "%d-%m-%Y_%Hh%Mm%S"

# OPX connection
CLUSTER_NAME = 'Cluster_1'
QOP_IP = '192.168.0.114'
QOP_PORT = 9510


"""
Load experiment configuration from the local module. 
"""
experiment_config = load_experiment_config_module(EXPERIMENT_CONFIG_PATH)
get_qua_config = experiment_config.get_qua_config  # function that returns the QUA config
BASE_SAVE_PATH = experiment_config.BASE_SAVE_PATH
CHIP_NAME = experiment_config.CHIP_NAME
COOLDOWN_NUMBER = experiment_config.COOLDOWN_NUMBER
RACK_NAME = experiment_config.RACK_NAME
EXP_CONFIG = experiment_config.EXP_CONFIG
INSTRUMENTS_CONFIG = experiment_config.INSTRUMENTS_CONFIG

COOLDOWN_SAVE_PATH = Path(BASE_SAVE_PATH, CHIP_NAME, f'cooldown_{COOLDOWN_NUMBER}')
