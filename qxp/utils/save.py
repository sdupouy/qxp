import inspect
from datetime import datetime
import pytz
import h5py
import json
from pathlib import Path, PurePosixPath
import numpy as np
import re
import os

from qxp.config import TIMESTAMP_FORMAT, DATA_DIRNAME, FIGURES_DIRNAME, DEBUG_SCRIPTS_DIRNAME, STORAGE_PATH, TIME_ZONE
from qxp.utils.database import current_chip, current_cooldown


def get_current_timestamp():
    """ Get the current timestamp as a tz-aware ISO formatted string. """
    local_timezone = pytz.timezone(TIME_ZONE)
    return datetime.now(local_timezone).isoformat()


def display_timestamp(timestamp):
    """ Formats a tz-aware ISO timestamp to a user-friendly string in local time (e.g. to create filenames). """
    local_timezone = pytz.timezone(TIME_ZONE)
    d = datetime.fromisoformat(timestamp).astimezone(local_timezone)  # ensure we display in the local timezone
    return d.strftime(TIMESTAMP_FORMAT)


def get_experiment_params(experiment):
    """ Get the experiment parameters as a dictionary.
    We filter out private attributes, the processed_config/data fields, and callables.
    Args:
        experiment: Experiment object.
    """
    def filter_key(k):
        if k.startswith('_'):
            return False
        if k == "processed_config" or k == "processed_data":
            return False  # processed_config/data is not saved as it can be recovered from the saved config/data
        return True
    experiment_params = {
        k: v for k, v in inspect.getmembers(experiment, lambda a: not callable(a)) if filter_key(k)
    }
    return experiment_params


def storage_path_from_db(path):
    """Resolve a stored database path to a filesystem path across OSes.

    The DB may contain Windows-style separators, while the webpanel runs on macOS/Linux.
    We keep the saved string convention unchanged and normalize only when turning it into a
    real filesystem path.
    """
    normalized = str(path).replace('\\', '/')
    relative = PurePosixPath(normalized)
    return Path(STORAGE_PATH, *relative.parts)


def cooldown_save_path():
    return Path(STORAGE_PATH) / current_chip().identifier / f'cooldown_{current_cooldown().number}'


def make_data_save_path(experiment_ident, timestamp):
    """ Return the saving path for an experiment's data, creating the directories if needed.
    Args:
        experiment_ident: Experiment identifier.
        timestamp: Experiment self.start_time.
    """
    timestamp = display_timestamp(timestamp)
    save_path = cooldown_save_path() / DATA_DIRNAME / experiment_ident
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.h5')
    return str(save_path)  # needs to be a string for HDF5 saving


def make_figure_save_path(experiment_ident, timestamp):
    """ Return the saving path for an experiment's figure, creating the directories if needed.
    Args:
        experiment_ident: Experiment identifier.
        timestamp: Experiment self.start_time.
    """
    timestamp = display_timestamp(timestamp)
    save_path = cooldown_save_path() / FIGURES_DIRNAME / experiment_ident
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.png')
    return save_path


def make_debug_script_save_path(experiment_ident, timestamp):
    """ Return the saving path for an experiment's debug script, creating the directories if needed.
    Args:
        experiment_ident: Experiment identifier.
        timestamp: Experiment self.start_time.
    """
    timestamp = display_timestamp(timestamp)
    save_path = cooldown_save_path() / DEBUG_SCRIPTS_DIRNAME / experiment_ident
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.py')
    return save_path  # must be a pathlib.Path object


def _worth_saving(value):
    """ Determine whether a value is worth saving to the datafile. """
    if value is None:
        return False
    if hasattr(value, '__len__'):
        return len(value) > 0
    return True


def _delete_key_if_exists(hdf_group: h5py.Group, key: str):
    """ Delete a key from an HDF5 group and group attributes if it exists. """
    # Delete dataset/group with that name if present
    if key in hdf_group:
        del hdf_group[key]
    # Delete attribute with that name if present
    if key in hdf_group.attrs:
        del hdf_group.attrs[key]
    # Also remove the masked-array companion dataset
    mask_key = f"_mask_{key}"
    if mask_key in hdf_group:
        del hdf_group[mask_key]


def _ensure_group(parent: h5py.Group, key: str) -> h5py.Group:
    """ Return an existing subgroup of parent; otherwise create it (and eventually delete prior content). """
    if key in parent:
        obj = parent[key]
        if isinstance(obj, h5py.Group):
            return obj
        del parent[key]  # dataset or other -> delete to replace with group

    # If an attribute with same key exists, remove it
    if key in parent.attrs:
        del parent.attrs[key]

    return parent.create_group(key)


def _recursively_save_dict(hdf_group: h5py.Group, dict_to_save: dict):
    """ Helper function to recursively save a dictionary to an open HDF5 group. """
    for key, value in dict_to_save.items():
        if _worth_saving(value):
            # We store the qua_config as a string as it contains lists of dicts which aren't HDF5-friendly
            if key == "qua_config":
                _delete_key_if_exists(hdf_group, key)
                hdf_group.create_dataset(key, data=json.dumps(value))

            # Save dictionaries recursively
            elif isinstance(value, dict):
                hdf_subgroup = _ensure_group(hdf_group, str(key))
                _recursively_save_dict(hdf_subgroup, value)

            # Save strings/ints/floats/bools as attributes
            elif isinstance(value, (str, int, float, bool)):
                hdf_group.attrs[key] = value

            # Save the data and mask of masked arrays separately
            elif isinstance(value, np.ma.MaskedArray):
                _delete_key_if_exists(hdf_group, key)  # will also delete the mask key
                hdf_group.create_dataset(key, data=value.data)
                hdf_group.create_dataset(f'_mask_{key}', data=value.mask)

            # Save other data types (typically ndarrays) as datasets
            else:
                _delete_key_if_exists(hdf_group, key)
                hdf_group.create_dataset(key, data=value)


def save_dict_to_hdf5(dict_to_save, save_path):
    """ Save dictionary to HDF5 file.
    Args:
        dict_to_save: Dictionary to save.
        save_path: Path to save HDF5 file.
    """
    with h5py.File(save_path, 'x') as hdf_file:  # Create the file and error if exists
        _recursively_save_dict(hdf_file, dict_to_save)


def update_dict_in_hdf5(dict_to_update, path, delete_first=False):
    """ Update an HDF5 file from a dictionary.
    Args:
        dict_to_update: Dictionary holding values to update.
        path: Path to the HDF5 file.
        delete_first: Whether to delete all dictionary keys from the HDF5 file first.
    """
    with h5py.File(path, 'r+') as hdf_file:  # Open existing file for read/write; error if it doesn't exist
        if delete_first:
            for key in dict_to_update.keys():
                _delete_key_if_exists(hdf_file, key)
        _recursively_save_dict(hdf_file, dict_to_update)


def load_dict_from_hdf5(path, keys=None):
    """ Load dictionary from HDF5 file.
    Args:
        path: Path to HDF5 file.
        keys: Keys to load. Load all keys if None (default). Nonexistent keys are silently skipped.
    """
    def _recursively_load_as_dict(hdf_group, keys=None):
        data_dict = {}
        for key, value in hdf_group.items():
            # Skip special keys; only keep keys asked for
            if key.startswith('_') or keys is not None and key not in keys:
                continue

            # The qua_config is stored as a string
            if key == "qua_config":
                data_dict[key] = json.loads(value[()])

            # If it's a group, recursively process it
            elif isinstance(value, h5py.Group):
                data_dict[key] = _recursively_load_as_dict(value)

            # Convert dataset to numpy array or masked array
            elif isinstance(value, h5py.Dataset):
                if f'_mask_{key}' in hdf_group:
                    mask = hdf_group[f'_mask_{key}']
                    data_dict[key] = np.ma.masked_array(value[()], mask=mask[()])
                else:
                    data_dict[key] = value[()]  # This reads the entire dataset into memory

        # Include attributes of the current group
        for key, value in hdf_group.attrs.items():
            if keys is None or key in keys:
                data_dict[key] = value
        return data_dict

    with h5py.File(path, 'r') as hdf_file:
        return _recursively_load_as_dict(hdf_file, keys=keys)


def make_json_serializable(obj):
    """ Try to make a dictionary serializable to JSON by converting numpy types to native python types. """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.bool_):  # Handle numpy bool
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def load_experiment(path, experiment):
    """ Load experiment from HDF5 file.
    Args:
        path: Path to HDF5 file.
        experiment: Experiment object that will get populated.
    """
    data_dict = load_dict_from_hdf5(path)
    for key, value in data_dict.items():
        setattr(experiment, key, value)


def get_latest_run_path(experiment_ident):
    """ Get the path of the latest run of an experiment. """
    save_path = cooldown_save_path() / DATA_DIRNAME / experiment_ident
    files = list(save_path.glob('*.h5'))
    return max(files, key=lambda x: datetime.strptime(x.stem, TIMESTAMP_FORMAT))


def figure_path_from_data_path(data_path):
    """ Find the figures path from the data path for a given experiment run. """
    data_path = PurePosixPath(str(data_path).replace('\\', '/'))
    parts = list(data_path.parts)
    parts[-3] = FIGURES_DIRNAME
    new_path = Path(*parts).with_suffix('.png')
    return new_path


def debug_script_path_from_data_path(data_path):
    """ Find the debug script path from the data path for a given experiment run. """
    data_path = PurePosixPath(str(data_path).replace('\\', '/'))
    parts = list(data_path.parts)
    parts[-3] = DEBUG_SCRIPTS_DIRNAME
    new_path = Path(*parts).with_suffix('.py')
    return new_path


def delete_file(path):
    """ Delete a file if it exists. """
    if os.path.isfile(path):
        try:
            os.remove(path)
            print(f"File '{path}' has been deleted.")
        except Exception as e:
            print(f"Error deleting file: {e}")
    else:
        print(f"File '{path}' does not exist.")
