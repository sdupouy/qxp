from abc import ABC, abstractmethod
import matplotlib.pyplot as plt

from qm import QuantumMachinesManager, SimulationConfig, generate_qua_script

from qxp.config import *
from qxp.utils.instruments import initialize_instruments
from qxp.utils.save import get_current_timestamp, get_experiment_params, get_latest_run_path, \
    load_experiment, save_dict_to_db, make_experiment_save_path, save_dict_to_hdf5


class BaseQuaExperiment(ABC):
    experiment_name = 'abstract_base_experiment'

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
        self.start_timestamp = None
        self.end_timestamp = None
        self.config_params = get_config_params()
        self.qua_config = get_qua_config(self.config_params)
        self.data = {}
        self.measured_params = {}
        self.save_path = None

    def set_default_parameters(self):
        """ Set the default parameters for the experiment. """
        pass

    def pre_process(self):
        """ Do the preprocessing (generally instrument setup). """
        initialize_instruments(self.config_params)

    @abstractmethod
    def get_qua_program(self):
        """ Define the QUA program. """
        pass

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
            if 'simulate_duration' in self.config_params:
                simulate_duration = self.config_params['simulate_duration']
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
        self.set_default_parameters()
        self.pre_process()
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

    def __str__(self):
        return f'{self.experiment_name}__{self.start_timestamp}'
