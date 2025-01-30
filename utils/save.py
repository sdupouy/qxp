from datetime import datetime
import inspect
import h5py
from pathlib import Path

from ..config import COOLDOWN_ID, SAVE_PATH


TIMESTAMP_FORMAT = "%d-%m-%Y_%Hh%M:%S"

def get_current_timestamp():
    """ Get the current timestamp as a string. """
    return datetime.now().strftime(TIMESTAMP_FORMAT)

def get_experiment_params(experiment):
    """ Get the experiment parameters as a dictionary.
    Args:
        experiment: Experiment object.
    """
    def filter_key(k):
        no_save_keys = ['simulate', 'save_data']  # These won't be saved
        if k.startswith('__'):
            return False
        if k in no_save_keys:
            return False
        return True
    experiment_params = {
        k: v for k, v in inspect.getmembers(experiment, lambda a: not callable(a)) if filter_key(k)
    }
    return experiment_params

def save_experiment(experiment_name, timestamp, dict_to_save):
    """ Save experimental data in cooldown_id/experiment_name/timestamp.h5.
    Args:
        experiment_name: Experiment name.
        timestamp: Timestamp.
        dict_to_save: Dictionary to save.
    """
    save_path = Path(SAVE_PATH, COOLDOWN_ID, experiment_name)
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.h5')
    save_dict_to_hdf5(dict_to_save, save_path)

def save_dict_to_hdf5(dict_to_save, save_path):
    """ Save dictionary to HDF5 file.
    Args:
        dict_to_save: Dictionary to save.
        save_path: Path to save HDF5 file.
    """
    def _recursively_save_dict(hdf_group, dict_to_save):
        for key, value in dict_to_save.items():
            if isinstance(value, dict):
                hdf_subgroup = hdf_group.create_group(key)
                _recursively_save_dict(hdf_subgroup, value)
            elif isinstance(value, str):
                hdf_group.attrs[key] = value  # Save strings as attributes
            else:
                hdf_group.create_dataset(key, data=value)  # Save other data types as datasets

    with h5py.File(save_path, 'x') as hdf_file:  # Create the file and error if exists
        _recursively_save_dict(hdf_file, dict_to_save)
