import inspect
from datetime import datetime
import h5py
from pathlib import Path

from qxp.config import COOLDOWN_ID, SAVE_PATH
from qxp.measurement_db.core.models import Parameter, Measurement, Cooldown, OpticalTable

# TODO: place in config
TIMESTAMP_FORMAT = "%d-%m-%Y_%Hh%M:%S"

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
        no_save_keys = [  # These won't be saved
            'simulate',
            'do_fit',
            'save_data',
            'update_calibration_db'
        ]
        if k.startswith('__'):
            return False
        if k in no_save_keys:
            return False
        return True
    experiment_params = {
        k: v for k, v in inspect.getmembers(experiment, lambda a: not callable(a)) if filter_key(k)
    }
    return experiment_params


def make_experiment_save_path(experiment_name, timestamp):
    """ Return the saving path for an experiment, creating the directories if needed.
    Args:
        experiment_name: Experiment name.
        timestamp: Experiment self.start_timestamp.
    """
    save_path = Path(SAVE_PATH, COOLDOWN_ID, experiment_name)
    save_path.mkdir(parents=True, exist_ok=True)
    save_path = save_path.joinpath(timestamp).with_suffix('.h5')
    return save_path


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


def load_dict_from_hdf5(path):
    """ Load dictionary from HDF5 file.
    Args:
        path: Path to HDF5 file.
    """
    def _recursively_load_as_dict(hdf_group):
        data_dict = {}
        for key, value in hdf_group.items():
            if isinstance(value, h5py.Group):
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
    save_path = Path(SAVE_PATH, COOLDOWN_ID, experiment_name)
    files = list(save_path.glob('*.h5'))
    return max(files, key=lambda x: datetime_from_timestamp(x.stem))


def save_dict_to_database(dict_to_save, exp_timestamp, data_path):
    """ Save dictionary to database.
    Args:
        dict_to_save: Dictionary to save.
        exp_timestamp: Experiment self.start_timestamp.
        data_path: Experiment self.save_path.
    """
    for key, value in dict_to_save.items():
        parameter = Parameter.objects.get_or_create(name=key)
        cooldown = Cooldown.objects.get(id=COOLDOWN_ID)
        optical_table = OpticalTable.objects.latest('datetime')
        measurement = Measurement(
            parameter=parameter,
            value=value,
            datetime=datetime_from_timestamp(exp_timestamp),
            cooldown=cooldown,
            optical_table=optical_table,
            data_path=data_path,
        )
        measurement.save()
