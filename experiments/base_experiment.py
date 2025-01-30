from abc import ABC, abstractmethod
import matplotlib.pyplot as plt

from qm import QuantumMachinesManager, SimulationConfig, generate_qua_script

from config import *
from utils.instruments import configure_instruments
from utils.save import get_current_timestamp, get_experiment_params, save_experiment


class BaseQuaExperiment(ABC):
    experiment_name = 'abstract_base_experiment'

    def __init__(self, simulate=False, save_data=True):
        self.simulate = simulate
        self.save_data = save_data
        self.start_timestamp = get_current_timestamp()
        self.end_timestamp = None
        self.config_params = get_config_params()
        self.qua_config = get_qua_config(self.config_params)
        self.data = {}

    def set_default_parameters(self):
        """ Set the default parameters for the experiment. """
        pass

    def pre_process(self):
        """ Do the preprocessing (generally instrument setup). """
        configure_instruments(self.config_params)

    @abstractmethod
    def get_qua_program(self):
        """ Define the QUA program. """
        pass

    def run_qua_program(self, prog):
        # Open Communication with the QOP
        qmm = QuantumMachinesManager(host=QOP_IP, port=QOP_PORT, cluster_name=CLUSTER_NAME)

        # Save the QUA debug script
        debug_script = generate_qua_script(prog=prog, config=self.qua_config)
        debug_script_path = SAVE_PATH / DEBUG_SCRIPTS_DIRECTORY / f'{self.experiment_name}_{self.start_timestamp}.py'
        with open(debug_script_path, 'w') as f_debug:
            f_debug.write(debug_script)

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

    def _set_self_data(self, results):
        self.data = self.get_data(results)

    def plot(self):
        pass

    def fit(self):
        pass

    def save(self):
        dict_to_save = get_experiment_params(self)
        save_experiment(self.experiment_name, self.start_timestamp, dict_to_save)

    def run(self):
        """ Run the experiment: set up, measure, analyze, plot and save. """
        self.set_default_parameters()
        self.pre_process()
        prog = self.get_qua_program()
        job = self.run_qua_program(prog)
        results = self.get_results(job)

        # do live plotting if the method is defined
        live_plotting = getattr(self, 'live_plotting', None)
        if callable(live_plotting):
            live_plotting(job, results)

        self._set_self_data(results)
        if self.save_data:
            self.save()
