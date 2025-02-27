import inspect
from datetime import datetime
import h5py
import json

from qxp.config import (COOLDOWN_SAVE_PATH, TIMESTAMP_FORMAT, CHIP_NAME, DATA_DIRNAME, FIGURES_DIRNAME,
                        DEBUG_SCRIPTS_DIRNAME)
from qxp.measurement_db.core.models import Measurement


def get_current_timestamp():
    """ Get the current timestamp as a string. """
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def datetime_from_timestamp(timestamp):
    """ Get a python datetime from a formatted timestamp. """
    return datetime.strptime(timestamp, TIMESTAMP_FORMAT)


def get_experiment_params(experiment):
    """ Get the experiment parameters as a dictionary.
    Args:
        experiment: Experiment object.
    """
    def filter_key(k):
        return not k.startswith('_')
    experiment_params = {
        k: v for k, v in inspect.getmembers(experiment, lambda a: not callable(a)) if filter_key(k)
    }
    return experiment_params


def make_data_save_path(experiment_name, timestamp):
    """ Return the saving path for an experiment's data, creating the directories if needed.
    Args:
        experiment_name: Experiment name.
        timestamp: Experiment self.start_timestamp.
    """
    save_path = COOLDOWN_SAVE_PATH / DATA_DIRNAME / experiment_name
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.h5')
    return str(save_path)  # needs to be a string for HDF5 saving


def make_figure_save_path(experiment_name, timestamp):
    """ Return the saving path for an experiment's figure, creating the directories if needed.
    Args:
        experiment_name: Experiment name.
        timestamp: Experiment self.start_timestamp.
    """
    save_path = COOLDOWN_SAVE_PATH / FIGURES_DIRNAME / experiment_name
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.png')
    return save_path


def make_debug_script_save_path(experiment_name, timestamp):
    """ Return the saving path for an experiment's debug script, creating the directories if needed.
    Args:
        experiment_name: Experiment name.
        timestamp: Experiment self.start_timestamp.
    """
    save_path = COOLDOWN_SAVE_PATH / DEBUG_SCRIPTS_DIRNAME / experiment_name
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.py')
    return save_path  # must be a pathlib.Path object


def save_dict_to_hdf5(dict_to_save, save_path):
    """ Save dictionary to HDF5 file.
    Args:
        dict_to_save: Dictionary to save.
        save_path: Path to save HDF5 file.
    """
    def _recursively_save_dict(hdf_group, dict_to_save):
        for key, value in dict_to_save.items():
            # We store the qua_config as a string as it contains lists of dicts which aren't HDF5-friendly
            if key == "qua_config":
                hdf_group.create_dataset(key, data=json.dumps(value))
            elif isinstance(value, dict):
                hdf_subgroup = hdf_group.create_group(str(key))
                _recursively_save_dict(hdf_subgroup, value)
            elif isinstance(value, (str, int, float, bool)):
                hdf_group.attrs[key] = value  # Save strings as attributes
            elif value is not None:
                hdf_group.create_dataset(key, data=value)  # Save other data types as datasets

    with h5py.File(save_path, 'x') as hdf_file:  # Create the file and error if exists
        _recursively_save_dict(hdf_file, dict_to_save)


def load_dict_from_hdf5(path):
    """ Load dictionary from HDF5 file.
    Args:
        path: Path to HDF5 file.
    """
    def _recursively_load_as_dict(hdf_group):
        data_dict = {}
        for key, value in hdf_group.items():
            # The qua_config is stored as a string
            if key == "qua_config":
                data_dict[key] = json.loads(value[()])
            elif isinstance(value, h5py.Group):
                # If it's a group, recursively process it
                data_dict[key] = _recursively_load_as_dict(value)
            elif isinstance(value, h5py.Dataset):
                # Convert dataset to numpy array
                data_dict[key] = value[()]  # This reads the entire dataset into memory
        # Include attributes of the current group
        data_dict.update(hdf_group.attrs)
        return data_dict

    with h5py.File(path, 'r') as hdf_file:
        return _recursively_load_as_dict(hdf_file)


def load_experiment(path, experiment):
    """ Load experiment from HDF5 file.
    Args:
        path: Path to HDF5 file.
        experiment: Experiment object that will get populated.
    """
    data_dict = load_dict_from_hdf5(path)
    for key, value in data_dict.items():
        setattr(experiment, key, value)


def get_latest_run_path(experiment_name):
    """ Get the path of the latest run of an experiment. """
    save_path = COOLDOWN_SAVE_PATH / experiment_name
    files = list(save_path.glob('*.h5'))
    return max(files, key=lambda x: datetime_from_timestamp(x.stem))


def fetch_last_from_db(parameter_name):
    """ Fetch last saved measurement from database.
    Args:
        parameter_name: The name of the parameter.
    """
    try:
        measurement = Measurement.objects.filter(
            experiment_run__cooldown__chip__name=CHIP_NAME,
            parameter__name=parameter_name
        ).order_by('experiment_run__datetime').last()
    except Measurement.DoesNotExist:
        measurement = None
    return measurement

