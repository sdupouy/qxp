from pathlib import Path

from utils.config import load_and_parse_parameters, load_experiment_config_module


EXPERIMENT_CONFIG_PATH = Path('experiments/autocat/config/experiment_config.py')
DEBUG_SCRIPTS_DIRECTORY = Path('debug_scripts')

# OPX connection
CLUSTER_NAME = 'Cluster_1'
QOP_IP = '192.168.0.114'
QOP_PORT = 9510


"""
Load experiment configuration from the local module. 
"""
experiment_config = load_experiment_config_module(EXPERIMENT_CONFIG_PATH)

def get_config_params():
    return load_and_parse_parameters(experiment_config.PARAMETERS_PATH)

def get_qua_config(config_params):
    return experiment_config.get_qua_config(config_params)

SAVE_PATH = experiment_config.SAVE_PATH
COOLDOWN_ID = experiment_config.COOLDOWN_ID
