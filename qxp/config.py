from pathlib import Path

from qxp.utils.config import load_experiment_config_module


EXPERIMENT_CONFIG_PATH = Path('experiments/autocat/config/experiment_config.py')
DEBUG_SCRIPTS_DIRECTORY = Path('debug_scripts')
TIMESTAMP_FORMAT = "%d-%m-%Y_%Hh%M:%S"

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
CONFIG_PARAMS = experiment_config.CONFIG_PARAMS

COOLDOWN_SAVE_PATH = Path(BASE_SAVE_PATH, CHIP_NAME, COOLDOWN_NUMBER)
