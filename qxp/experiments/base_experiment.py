from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from qm import QuantumMachinesManager, SimulationConfig, generate_qua_script

from qxp.config import EXP_CONFIG, get_qua_config, QOP_IP, QOP_PORT, CLUSTER_NAME, COOLDOWN_SAVE_PATH, \
    DEBUG_SCRIPTS_DIRECTORY, INSTRUMENTS_CONFIG
from qxp.utils.config import update_nested_dict
from qxp.utils.instruments import initialize_instruments_from_config, turn_off_instruments_from_config
from qxp.utils.save import get_current_timestamp, get_experiment_params, get_latest_run_path, \
    load_experiment, save_dict_to_db, make_experiment_save_path, save_dict_to_hdf5


class BaseQuaExperiment(ABC):
    experiment_name = 'abstract_base_qua_experiment'

    def __init__(self, simulate=False, do_fit=True, do_save=True, do_update_db=False):
        """ Initialize the experiment.
        Args:
              simulate (bool, optional): Whether to simulate the experiment.
              do_fit (bool, optional): Whether to fit the experiment.
              do_save (bool, optional): Whether to save the data.
              do_update_db (bool, optional): Whether to update the calibration database.
        """
        self.simulate = simulate
        self.do_fit = do_fit
        self.do_save = do_save
        self.do_update_db = do_update_db
        self.start_timestamp = None  # set in self.run()
        self.end_timestamp = None  # set in self.run()
        self.exp_config = {}  # set in self.configure()
        self.instruments_config = {}  # set in self.configure()
        self.qua_config = {}  # set in self.configure()
        self.data = {}  # returned by self.get_data()
        self.measured_params = {}  # returned by self.fit()
        self.save_path = None  # set in self.save()

    @abstractmethod
    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        pass

    @abstractmethod
    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        pass

    @abstractmethod
    def get_qua_program(self):
        """ Define the QUA program. """
        pass

    @abstractmethod
    def get_results(self, job):
        pass

    @abstractmethod
    def get_data(self, results):
        """ Return the dictionary containing the data. """
        pass

    @abstractmethod
    def plot(self):
        pass

    @abstractmethod
    def fit(self, axs=None):
        pass

    def initialize_instruments(self):
        initialize_instruments_from_config(self.instruments_config)

    def turn_off_instruments(self):
        turn_off_instruments_from_config(self.instruments_config)

    def run_qua_program(self, prog):
        # Open Communication with the QOP
        qmm = QuantumMachinesManager(host=QOP_IP, port=QOP_PORT, cluster_name=CLUSTER_NAME)

        # Save the QUA debug script
        debug_script = generate_qua_script(prog=prog, config=self.qua_config)
        debug_script_path = (
                COOLDOWN_SAVE_PATH
                / DEBUG_SCRIPTS_DIRECTORY
                / f'{self.experiment_name}_{self.start_timestamp}.py'
        )
        debug_script_path.write_text(debug_script)

        # Simulate or execute
        if self.simulate:
            if 'simulate_duration' in self.exp_config:
                simulate_duration = self.exp_config['simulate_duration']
            else:
                simulate_duration = 10_000  # In clock cycles = 4ns
            simulation_config = SimulationConfig(duration=simulate_duration)
            job = qmm.simulate(self.qua_config, prog, simulation_config)
            job.get_simulated_samples().con1.plot()
            plt.show()
            exit()
        else:
            qm = qmm.open_qm(self.qua_config)
            job = qm.execute(prog)
            return job

    def save_measured_params_to_db(self):
        if self.measured_params:
            save_dict_to_db(self.measured_params, self.start_timestamp, self.save_path)
        else:
            print("[!] No measured values to save to database. Is do_fit=True?")

    def save(self):
        """ Save the experiment parameters and data in the HDF5 format. """
        self.save_path = make_experiment_save_path(self.experiment_name, self.start_timestamp)
        dict_to_save = get_experiment_params(self)
        save_dict_to_hdf5(dict_to_save, self.save_path)

    def load(self, path=None):
        """ Load saved data. If path is None the latest run will be loaded. """
        if path is None:
            path = get_latest_run_path(self.experiment_name)
        load_experiment(self, path)

    def run(self):
        """ Run the experiment: set up, measure, analyze, plot and save. """
        self.start_timestamp = get_current_timestamp()
        self.initialize_instruments()
        prog = self.get_qua_program()
        job = self.run_qua_program(prog)
        results = self.get_results(job)

        # do live plotting if the method is defined
        live_plotting = getattr(self, 'live_plotting', None)
        if callable(live_plotting):
            live_plotting(job, results)

        self.data = self.get_data(results)
        self.end_timestamp = get_current_timestamp()
        if self.do_fit:
            self.measured_params = self.fit()
        if self.do_save:
            self.save()
        if self.do_update_db:
            self.save_measured_params_to_db()

    def configure(self, force_exp_config=None, force_instruments_config=None):
        """ Build experiment, instruments, and QUA configuration dictionaries.
        Args:
            force_exp_config (dict, optional): Dictionary to override values of the experiment config.
            force_instruments_config (dict, optional): Dictionary to override values of the instruments config.
        """
        self.exp_config = EXP_CONFIG
        self.instruments_config = INSTRUMENTS_CONFIG
        self.auto_set_exp_config()
        if force_exp_config is not None:
            update_nested_dict(self.exp_config, force_exp_config)
        self.auto_set_instruments_config()
        if force_instruments_config is not None:
            update_nested_dict(self.instruments_config, force_instruments_config)
        self.qua_config = get_qua_config(self.exp_config)

    def configure_and_run(self, force_exp_config=None, force_instruments_config=None):
        """ Automatically configure and run the experiment.
        Args:
            force_exp_config (dict, optional): Dictionary to override values of the experiment config.
            force_instruments_config (dict, optional): Dictionary to override values of the instruments config.
        """
        self.configure(force_exp_config, force_instruments_config)
        self.run()

    def __str__(self):
        return f'{self.experiment_name}__{self.start_timestamp}'
