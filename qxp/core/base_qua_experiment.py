from abc import ABC, abstractmethod
import sys
import threading
import matplotlib.pyplot as plt
from qm import QuantumMachinesManager, SimulationConfig, generate_qua_script

from qxp.config import EXP_CONFIG, get_qua_config, OPX_CONNECTION, INSTRUMENTS_CONFIG, MPLSTYLE_PATH
from qxp.utils.config import update_nested_dict
from qxp.utils.database import current_cooldown
from qxp.utils.instruments import initialize_instruments_from_config, turn_off_instruments_from_config
from qxp.utils.save import get_current_timestamp, get_experiment_params, get_latest_run_path, \
    save_dict_to_hdf5, load_dict_from_hdf5, datetime_from_timestamp, make_figure_save_path, \
    make_debug_script_save_path, make_data_save_path
from qxp.measurement_db.core.models import OpticalTable, ExperimentRun, Parameter, Measurement, Experiment

plt.style.use(MPLSTYLE_PATH)


class BaseQuaExperiment(ABC):
    """
    Base experiment class for a QUA experiment.
    The class should be inherited by your own experiment classes. It factorizes out common patterns (such as
    launching the QUA program, saving the data, loading saved data, updating the database) and enforces structured code.
    The following methods are declared as abstract methods and have to be redefined in the inherited class:
    - auto_set_exp_config()
    - auto_set_instruments_config()
    - get_qua_program()
    - get_data(result_handles)
    - fit()
    - plot()
    The following methods can be optionally implemented in the inherited classes:
    - live_plotting(): Manage the live-plotting loop that will be run in a separate thread during the
        execution of the program.
    - manage_job_pauses(job, result_handles): Check when the job is paused, and decide what to do. Typical usage is to
        define outer instrument loops.

    Example usage (replace the base experiment by one of its inherited class):
    ```
    experiment = BaseQuaExperiment()
    experiment.configure_and_run()
    ```
    """
    identifier = 'abstract_base_qua_experiment'  # the name of the experiment, to be used as a unique identifier (e.g. to build file names)
    display_name = 'Abstract base QUA experiment'  # the name of the experiment, to be printed

    def __init__(self, comment=""):
        """ Initialize the experiment.
        Args:
              comment: A comment that will be stored with the experiment run.
        """
        self.comment = comment
        self.start_timestamp = None  # set in self.run()
        self.end_timestamp = None  # set in self.run()
        self.exp_config = {}  # set in self.configure()
        self.instruments_config = {}  # set in self.configure()
        self.qua_config = {}  # set in self.configure()
        self.data = {}  # returned by self.get_data()
        self.fit_params = {}  # set by self.fit(), typically popt
        self.measured_db_params = {}  # returned by self.fit(), to be saved to database
        self.save_path = None  # set in self.save()
        self.experiment_run_id = None  # set in log_experiment_run_to_db()

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
    def get_data(self, result_handles):
        """ Return the dictionary containing the data. """
        pass

    @abstractmethod
    def fit(self):
        """
        Fit the data.
        This method can set self.fit_params to be used by self.plot.
        It should return a flat dictionary containing the measured parameters to be saved to the database.
        """
        pass

    @abstractmethod
    def plot(self):
        """ Plot the data and return a matplotlib figure. """
        pass

    def initialize_instruments(self):
        initialize_instruments_from_config(self.instruments_config)

    def turn_off_instruments(self):
        turn_off_instruments_from_config(self.instruments_config)

    def run_qua_program(self, prog, simulate=False):
        # Open Communication with the QOP
        qmm = QuantumMachinesManager(
            host=OPX_CONNECTION['host'],
            port=OPX_CONNECTION['port'],
            cluster_name=OPX_CONNECTION['cluster_name']
        )

        # Save the QUA debug script
        debug_script = generate_qua_script(prog=prog, config=self.qua_config)
        debug_script_path = make_debug_script_save_path(self.identifier, self.start_timestamp)
        debug_script_path.write_text(debug_script)

        # Simulate or execute
        if simulate:
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

    def save(self):
        """ Save the experiment parameters and data in the HDF5 format. """
        self.save_path = make_data_save_path(self.identifier, self.start_timestamp)
        dict_to_save = get_experiment_params(self)

        # Save the code of the experiment module
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name)
        with open(module.__file__, 'r') as f:
            experiment_code = f.read()
        dict_to_save['experiment_code'] = experiment_code

        save_dict_to_hdf5(dict_to_save, self.save_path)
        print('[+] Saved experiment to', self.save_path)

    def load(self, path=None):
        """ Load saved data. If path is None the latest run will be loaded. """
        if path is None:
            path = get_latest_run_path(self.identifier)
        data_dict = load_dict_from_hdf5(path)
        for key, value in data_dict.items():
            setattr(self, key, value)

    def log_experiment_run_to_db(self):
        """ Log the experiment run in the measurement database. """
        experiment = Experiment.objects.get_or_create(
            name=self.identifier,
            defaults={
                'display_name': self.display_name,
                'description': (self.__doc__ or '').replace('\t', ''),
                'module_name': self.__class__.__module__,
            }
        )[0]
        optical_table = OpticalTable.objects.latest('datetime')
        experiment_run = ExperimentRun(
            experiment=experiment,
            datetime=datetime_from_timestamp(self.start_timestamp),
            cooldown=current_cooldown(),
            optical_table=optical_table,
            data_path=self.save_path,
            comment=self.comment,
        )
        experiment_run.save()
        print("[+] Logged experiment run to database")
        self.experiment_run_id = experiment_run.id

    def save_measured_params_to_db(self):
        """ Save the measured parameters to the database. """
        if self.measured_db_params:
            experiment_run = ExperimentRun.objects.get(id=self.experiment_run_id)
            for key, value in self.measured_db_params.items():
                if isinstance(value, (tuple, list)) and len(value) == 2:
                    value, uncertainty = value  # unpack (value, uncertainty) tuples
                else:
                    uncertainty = None
                parameter = Parameter.objects.get_or_create(identifier=key)[0]
                measurement = Measurement(
                    parameter=parameter,
                    value=value,
                    uncertainty=uncertainty,
                    experiment_run=experiment_run,
                )
                measurement.save()
            print("[+] Saved measured parameters to database")
        else:
            print("[!] No measured values to save to database. Is do_fit=True?")

    def run(self, simulate=False, do_fit=True, do_plot=True, do_save=True, do_update_db=False):
        """ Run the experiment: set up, measure, analyze, plot and save.
        Args:
            simulate (bool): Simulate the QUA program instead of running it.
            do_fit (bool): Whether to fit the data.
            do_plot (bool): Whether to plot the data.
            do_save (bool): Whether to save the data.
            do_update_db (bool): Whether to update the database.
        """
        print('[+] Running', self.identifier)
        self.start_timestamp = get_current_timestamp()
        self.initialize_instruments()
        prog = self.get_qua_program()
        job = self.run_qua_program(prog, simulate)
        result_handles = job.result_handles

        # do live plotting if the method is defined
        live_plotting_thread = None
        live_plotting = getattr(self, 'live_plotting', None)
        if callable(live_plotting):
            live_plotting_thread = threading.Thread(target=live_plotting, args=(job,), daemon=True)
            print('[+] Starting live plotting thread')
            live_plotting_thread.start()

        # manage job pauses (run outer loops) if the method is defined
        manage_job_pauses = getattr(self, 'manage_job_pauses', None)
        if callable(manage_job_pauses):
            manage_job_pauses(job)

        if live_plotting_thread:
            live_plotting_thread.join()  # wait for the thread to terminate (normally when the job finished processing)

        result_handles.wait_for_all_values()
        self.data = self.get_data(result_handles)
        self.end_timestamp = get_current_timestamp()

        if do_fit:
            self.measured_db_params = self.fit()

        if do_plot:
            fig = self.plot()
            fig_path = make_figure_save_path(self.identifier, self.start_timestamp)
            fig.savefig(fig_path)
            print("[+] Saved figure at", fig_path)

        if do_save:
            self.save()
            self.log_experiment_run_to_db()

        if do_update_db:
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
        self.qua_config = get_qua_config(self.exp_config, self.instruments_config)

    def configure_and_run(self, force_exp_config=None, force_instruments_config=None,
                          simulate=False, do_fit=True, do_plot=True, do_save=True, do_update_db=False):
        """ Automatically configure and run the experiment.
        Args:
            force_exp_config (dict, optional): Dictionary to override values of the experiment config.
            force_instruments_config (dict, optional): Dictionary to override values of the instruments config.
            simulate (bool): Simulate the QUA program instead of running it.
            do_fit (bool): Whether to fit the data.
            do_plot (bool): Whether to plot the data.
            do_save (bool): Whether to save the data.
            do_update_db (bool): Whether to update the database.
        """
        self.configure(force_exp_config, force_instruments_config)
        self.run(simulate=simulate, do_fit=do_fit, do_plot=do_plot, do_save=do_save, do_update_db=do_update_db)

    def __str__(self):
        return f'{self.identifier}__{self.start_timestamp}'
