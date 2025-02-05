import importlib.util


def load_experiment_config_module(experiment_config_path):
    """ Load the experiment_config module.
    Args:
        experiment_config_path (Path): The path to the experiment_config module,
            usually `qxp/experiments/your_project/config/experiment_config.py`.
    """
    if experiment_config_path.exists():
        spec = importlib.util.spec_from_file_location("experiment_config", experiment_config_path)
        experiment_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(experiment_module)
        return experiment_module
    else:
        raise FileNotFoundError(f"Experiment configuration file not found: {str(experiment_config_path)}")


def update_nested_dict(target_dict, update_dict):
    """ Updates a target dictionary recursively from another dictionary.
    Args:
        target_dict: The dictionary to update (existing data).
        update_dict: The dictionary containing updates.
    """
    for key, value in update_dict.items():
        if key in target_dict:
            if isinstance(target_dict[key], dict) and isinstance(value, dict):
                update_nested_dict(target_dict[key], value)
            elif not isinstance(target_dict[key], dict) and not isinstance(value, dict):
                target_dict[key] = value
            else:
                print(f"[!] Updating '{key}' failed as it is not a dictionary in target or update.")
        else:
            target_dict[key] = value
