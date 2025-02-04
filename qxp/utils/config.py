import importlib.util


def load_experiment_config_module(experiment_config_path):
    if experiment_config_path.exists():
        spec = importlib.util.spec_from_file_location("experiment_config", experiment_config_path)
        experiment_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(experiment_module)
        return experiment_module
    else:
        raise FileNotFoundError(f"Experiment configuration file not found: {experiment_config_path}")
