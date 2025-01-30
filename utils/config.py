import json
from typing import Tuple, Dict
from pathlib import Path
import importlib.util

import numpy as np


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"No such file: '{path}'")

    with path.open('r', encoding='utf-8') as file:
        return json.load(file)


def parse_parameter(parameter: Tuple):
    value, unit, type_string = parameter

    if isinstance(value, list):
        # handle lists, like IQ mixer correction matrix
        parsed_value = []
        for sub_value in value:
            parsed_value.append(parse_parameter((sub_value, unit, type_string)))
    else:
        match unit:
            case 'GHz':
                parsed_value = value * 1e9
            case 'MHz':
                parsed_value = value * 1e6
            case 'kHz':
                parsed_value = value * 1e3
            case 'hz':
                parsed_value = value

            case 'ns':
                parsed_value = value
            case 'us':
                parsed_value = value * 1e3
            case 'ms':
                parsed_value = value * 1e6

            case "dBm":
                parsed_value = value

            case "kOhm":
                parsed_value = value * 1e3
            case "MOhm":
                parsed_value = value * 1e6

            case "V":
                parsed_value = value
            case "mV":
                parsed_value = value * 1e-3

            case '2pi':
                parsed_value = value * 2 * np.pi
            case 'pi':
                parsed_value = value * np.pi

            case 'arb':
                parsed_value = value
            case _:
                raise ValueError(f'Invalid parameter unit for {parameter}')

        match type_string:
            case 'int':
                parsed_value = int(parsed_value)
            case 'float':
                parsed_value = float(parsed_value)
            case 'bool':
                parsed_value = bool(parsed_value)
            case _:
                raise ValueError(f'Invalid parameter type for {parameter}')

    return parsed_value


def parse_dict(unparsed_dict: Dict):
    parsed_dict = {}
    for key, value in unparsed_dict.items():
        if isinstance(value, dict):
            parsed_dict[key] = parse_dict(value)  # Recursively parse sub-dictionaries
        else:
            parsed_dict[key] = parse_parameter(value)  # Parse the value
    return parsed_dict


def load_and_parse_parameters(parameters_path: Path):
    unparsed_dict = load_json(parameters_path)
    parsed_dict = parse_dict(unparsed_dict)
    return parsed_dict

def load_experiment_config_module(experiment_config_path):
    if experiment_config_path.exists():
        spec = importlib.util.spec_from_file_location("experiment_config", experiment_config_path)
        experiment_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(experiment_module)
        return experiment_module
    else:
        raise FileNotFoundError(f"Experiment configuration file not found: {experiment_config_path}")
