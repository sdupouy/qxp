from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, is_dataclass
from typing import ClassVar, Optional, Any
import inspect
from datetime import datetime
import sys
import threading

import matplotlib.pyplot as plt
import numpy as np
from tqdm.auto import tqdm
from qm import QuantumMachinesManager, SimulationConfig, generate_qua_script
from qualang_tools.plot import interrupt_on_close

from qxp.config import EXP_CONFIG, get_qua_config, OPX_CONNECTION, INSTRUMENTS_CONFIG, MPLSTYLE_PATH, FORCE_EXP_CONFIG, \
    FORCE_INSTRUMENTS_CONFIG
from qxp.utils.config import update_nested_dict
from qxp.utils.database import current_cooldown
from qxp.utils.instruments import initialize_instruments_from_config, turn_off_instruments_from_config
from qxp.utils.save import get_current_timestamp, get_experiment_params, get_latest_run_path, \
    save_dict_to_hdf5, update_dict_in_hdf5, load_dict_from_hdf5, make_figure_save_path, \
    make_debug_script_save_path, make_data_save_path, display_timestamp
from qxp.utils.units import try_to_match_units
from qxp.measurement_db.core.models import OpticalTable, ExperimentRun, Parameter, Measurement, Experiment

plt.style.use(MPLSTYLE_PATH)


@dataclass(eq=False, kw_only=True)
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
    - initialize_plot()
    - update_plot(updatables)
    The following methods can be optionally implemented in the inherited classes:
    - process_config()
    - pre_run(qm)
    - process_data()
    - progress()
    - validate()
    - manage_job_pauses(job, result_handles): Check when the job is paused, and decide what to do. Typical usage is to
        define outer instrument loops.

    Example usage (replace the base experiment by one of its inherited class):
    ```
    experiment = BaseQuaExperiment()
    experiment.configure_and_run()
    ```
    """
    # Class metadata that must be redefined in subclasses
    identifier: ClassVar[str] = ''  # the name of the experiment, to be used as a unique identifier (e.g. to build file names)
    display_name: ClassVar[str] = ''  # the name of the experiment, to be printed

    # Base fields (optional init parameters)
    comment: str = field(default="", metadata={'qxp_base': True})

    # Base fields (never init parameters)
    start_time: Optional[str] = field(default=None, init=False, repr=False)  # set in self.run() - ISO format and tz-aware
    end_time: Optional[str] = field(default=None, init=False, repr=False)  # set in self.run() - ISO format and tz-aware
    exp_parameters: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # deep copy of the instantiation arguments, set in self.run()
    exp_config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # set in self.configure()
    instruments_config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # set in self.configure()
    qua_config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # set in self.configure()
    processed_config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # returned by self.process_config - NOT SAVED
    pre_run_data: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # set in self._run_qua_program if self.pre_run is defined
    data: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # returned by self.get_data()
    processed_data: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # returned by self.process_data() - NOT SAVED
    execution_report: Optional[str] = field(default=None, init=False, repr=False)  # QmJob.execution_report(), set after job ends
    fit_params: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # set by self.fit(), typically popt
    measured_db_params: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # returned by self.fit(), to be saved to database
    save_path: Optional[str] = field(default=None, init=False, repr=False)  # set in self.save()

    def __init_subclass__(cls, **kwargs):
        """ Enforce definition of some class variables. """
        super().__init_subclass__(**kwargs)

        if not inspect.isabstract(cls):
            if not cls.identifier:
                raise TypeError(f"{cls.__qualname__} must define class attribute 'identifier: str'")
            if not cls.display_name:
                raise TypeError(f"{cls.__qualname__} must define class attribute 'display_name: str'")

    @staticmethod
    def _snapshot_value(v):
        """
        Return a snapshot of a value.
        Used to make `self.exp_parameters` reliable. Can be extended in a subclass if needed (for unusual types).
        """
        if isinstance(v, np.ndarray):
            return v.copy()
        if isinstance(v, (dict, list, tuple, set)):
            return copy.deepcopy(v)
        return v

    @abstractmethod
    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        pass

    @abstractmethod
    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        pass

    def process_config(self):
        """
        Process the configuration to extract values that make sense to plot.
        Return a dictionary of processed configuration parameters that will be stored in self.processed_config,
        but not saved on disk.
        Should generally be called after self.configure.
        """
        return {}

    def pre_run(self, qm):
        """
        Run a measurement or setup just before the main QUA program is executed.
        Does nothing unless redefined in the child class.
        """
        return {}

    @abstractmethod
    def get_qua_program(self):
        """ Define the QUA program. """
        pass

    @abstractmethod
    def get_data(self, result_handles):
        """
        Return the dictionary containing the unprocessed data, that will be saved to self.data.
        Ensure that some data is available before calling.
        """
        pass

    def process_data(self):
        """
        Process self.data to extract values that make sense to plot.
        Return a dictionary of processed data that will be stored in self.processed_data, but not saved on disk.
        Should generally be called after self.get_data.
        """
        return {}

    def progress(self):
        """ Return the percentage of progress, or None if not implemented. """
        return None

    @abstractmethod
    def fit(self):
        """
        Fit the data.
        This method can set self.fit_params to be used by self.plot.
        It should return a flat dictionary containing the measured parameters to be saved to the database.
        """
        pass

    def validate(self):
        """ Validate whether the measurements were successful.
        Returns:
            A boolean determining whether all measured parameters are valid, or a dictonary of booleans where keys
            indicate a specific parameter name.
        """
        return False

    @abstractmethod
    def initialize_plot(self):
        """ Create a matplotlib figure. Return a dictionary of objects to update. """
        pass

    @abstractmethod
    def update_plot(self, updatables):
        """ Update the plot. """
        pass

    def plot(self):
        """ Initialize and update the plot with self.data. """
        updatables = self.initialize_plot()
        self.update_plot(updatables)

    def _live_plot(self, job):
        """ Do the live plotting. """
        print("[+] Starting live plotting.")
        updatables = self.initialize_plot()
        interrupt_on_close(plt.gcf(), job)  # Interrupt the job when the user closes the figure

        # Wait for the first results
        for v in job.result_handles.values():
            v.wait_for_values(1)

        self.data = self.get_data(job.result_handles)  # must be called before self.progress()
        self.processed_data = self.process_data()
        self.update_plot(updatables)

        # Initialize the progress bar
        pbar = None
        prev_progress = self.progress()
        if prev_progress is not None:
            pbar = tqdm(
                total=100,
                bar_format="Progress: |{bar}| {percentage:3.1f}% [{elapsed}<{remaining}]",
                dynamic_ncols=True,
                initial=prev_progress,
            )

        plt.pause(3)

        # Live plotting loop
        while job.result_handles.is_processing():
            # Fetch and update
            self.data = self.get_data(job.result_handles)
            self.processed_data = self.process_data()
            self.update_plot(updatables)

            # Show the progress bar
            if pbar is not None:
                progress = self.progress()
                progress_delta = progress - prev_progress
                if progress_delta > 0:
                    pbar.update(progress_delta)
                    prev_progress = progress

            # Wait for 3 seconds
            plt.pause(3)

        if pbar is not None:
            pbar.update(100 - pbar.n)  # mark the progress complete before closing
            pbar.close()

    def _capture_exp_parameters(self):
        """
        Capture user-defined experiment parameters (fields with init=True that are not marked 'qxp_base').
        Stores snapshot into self.exp_parameters.
        """
        for f in fields(self):
            if not f.init:
                continue
            if f.metadata.get("qxp_base", False):
                continue
            self.exp_parameters[f.name] = self._snapshot_value(getattr(self, f.name))

    def initialize_instruments(self):
        initialize_instruments_from_config(self.instruments_config)

    def turn_off_instruments(self):
        turn_off_instruments_from_config(self.instruments_config)

    def _run_qua_program(self, prog, simulate=False):
        # Open Communication with the QOP
        qmm = QuantumMachinesManager(
            host=OPX_CONNECTION['host'],
            port=OPX_CONNECTION['port'],
            cluster_name=OPX_CONNECTION['cluster_name']
        )

        # Save the QUA debug script
        debug_script = generate_qua_script(prog=prog, config=self.qua_config)
        debug_script_path = make_debug_script_save_path(self.identifier, self.start_time)
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
            return None
        else:
            qm = qmm.open_qm(self.qua_config)
            self.pre_run_data = self.pre_run(qm)  # does nothing if not redefined in the child class
            job = qm.execute(prog)
            return job

    def save(self):
        """ Save the experiment parameters and data in the HDF5 format. """
        self.save_path = make_data_save_path(self.identifier, self.start_time)
        dict_to_save = get_experiment_params(self)

        # Save the code of the experiment module
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name)
        with open(module.__file__, 'r') as f:
            experiment_code = f.read()
        dict_to_save['experiment_code'] = experiment_code

        save_dict_to_hdf5(dict_to_save, self.save_path)
        print('[+] Saved experiment to', self.save_path)

    def load(self, path=None, process_config=True, process_data=True):
        """ Load saved data.
        Args:
            path (optional): The path to the hdf5 file. If None, the latest run will be loaded.
            process_config (optional): Whether to process the configuration upon loading.
            process_data (optional): Whether to process the data upon loading.
        Returns:
            The experiment instance.
        """
        if path is None:
            path = get_latest_run_path(self.identifier)

        data_dict = load_dict_from_hdf5(path)
        for key, value in data_dict.items():
            setattr(self, key, value)

        if process_config:
            self.processed_config = self.process_config()
        if process_data:
            self.processed_data = self.process_data()
        return self  # so we can do `exp = ExpClass.load()`

    def log_experiment_run_to_db(self):
        """ Log the experiment run in the measurement database. """
        experiment = Experiment.objects.get_or_create(
            identifier=self.identifier,
            defaults={
                'display_name': self.display_name,
                'description': (self.__doc__ or '').replace('\t', '').strip('\r\n '),
                'module_name': self.__class__.__module__,
            }
        )[0]
        optical_table = OpticalTable.objects.latest('datetime')
        experiment_run = ExperimentRun(
            experiment=experiment,
            datetime=datetime.fromisoformat(self.start_time),
            datetime_end=datetime.fromisoformat(self.end_time),
            cooldown=current_cooldown(),
            optical_table=optical_table,
            data_path=self.save_path,
            comment=self.comment,
        )
        experiment_run.save()
        print("[+] Logged experiment run to database")

    def save_measured_params_to_db(self, are_valid):
        """ Save the measured parameters to the database.
        Args:
            are_valid (bool or dict): Whether the measured parameters are valid. Can be a boolean, which then applies
                to all measured parameters, or a dictionary of booleans where the keys are the parameter names.
        """
        if self.measured_db_params:
            experiment_run = ExperimentRun.objects.get(datetime=datetime.fromisoformat(self.start_time))
            for key, value_dict in self.measured_db_params.items():
                value = value_dict['value']
                uncertainty = value_dict.get('uncertainty')
                unit = value_dict.get('unit')

                # Determine whether the measurement is valid
                if isinstance(are_valid, dict):
                    is_valid = are_valid[key]
                else:
                    is_valid = are_valid

                # Extract or create the parameter in the database
                parameter, _ = Parameter.objects.get_or_create(
                    identifier=key,
                    defaults={'unit': unit}
                )

                # Try to match units if they are not the same
                unit_db = parameter.unit
                if (unit_db or unit) and unit_db != unit:
                    print(f"Attempting to match units {parameter} and {unit_db}")
                    multiplier = try_to_match_units(unit, unit_db)
                    if multiplier is not None:
                        unit *= multiplier
                    else:
                        print(f"[!] Units could not be matched, {key} not saved to database")
                        continue

                measurement = Measurement(
                    parameter=parameter,
                    value=value,
                    uncertainty=uncertainty,
                    experiment_run=experiment_run,
                    is_valid=is_valid
                )
                measurement.save()
                print(f"[+] Saved measured parameter {key} to database")
        else:
            print("[!] No measured values to save to database. Is do_fit=True?")

    def delete_measured_params_from_db(self):
        """ Delete all measured parameters associated to this run from the database. """
        experiment_run = ExperimentRun.objects.get(datetime=datetime.fromisoformat(self.start_time))
        Measurement.objects.filter(experiment_run=experiment_run).delete()

    def run(self, simulate=False, do_fit=True, do_plot=True, do_save=True, validate='auto',
            print_execution_report=False):
        """ Run the experiment: set up, measure, analyze, plot and save.
        Args:
            simulate (bool): Simulate the QUA program instead of running it.
            do_fit (bool): Whether to fit the data.
            do_plot (bool): Whether to plot the data.
            do_save (bool): Whether to save the data.
            validate (str): Whether to validate the data. Can take 'yes', 'no' or 'auto' (default), which relies on the
                `validate` method to determine if the measurements should be validated.
            print_execution_report (bool): Whether to print the QM job execution report after it is completed.
        """
        self._capture_exp_parameters()
        self.start_time = get_current_timestamp()

        if simulate:
            print('[+] Simulating', self.identifier)
        else:
            print('[+] Running', self.identifier)
            self.initialize_instruments()

        # prepare the main job
        prog = self.get_qua_program()
        job = self._run_qua_program(prog, simulate)
        if job is None:  # happens if simulate=True
            return
        result_handles = job.result_handles

        # manage job pauses (run outer loops) if the method is defined
        job_management_thread = None
        manage_job_pauses = getattr(self, 'manage_job_pauses', None)
        if callable(manage_job_pauses):
            job_management_thread = threading.Thread(target=manage_job_pauses, args=(job,), daemon=True)
            print('[+] Starting job management thread')
            job_management_thread.start()

        self._live_plot(job)

        if job_management_thread:
            job_management_thread.join()  # wait for the thread to terminate (normally when the job finished processing)

        result_handles.wait_for_all_values()
        self.data = self.get_data(result_handles)
        self.end_time = get_current_timestamp()
        self.execution_report = str(job.execution_report())
        if print_execution_report:
            print(self.execution_report)
        self.processed_data = self.process_data()

        if do_fit:
            try:
                self.measured_db_params = self.fit()
            except Exception as e:
                self.fit_params = {}  # ensure fit won't be plotted
                print("[!] Fit failed:", e)

        plt.close()  # close the live plot if it still open
        if do_plot:
            self.plot()
            if do_save:
                fig_path = make_figure_save_path(self.identifier, self.start_time)
                plt.gcf().savefig(fig_path)
                print("[+] Saved figure at", fig_path)
            plt.close()

        if do_save:
            self.save()
            self.log_experiment_run_to_db()

            match validate:
                case 'yes':
                    are_valid = True
                case 'no':
                    are_valid = False
                case 'auto':
                    are_valid = self.validate()
            self.save_measured_params_to_db(are_valid)

    def configure(self, force_exp_config=None, force_instruments_config=None):
        """ Build experiment, instruments, and QUA configuration dictionaries.
        Args:
            force_exp_config (dict, optional): Dictionary to override values of the experiment config.
            force_instruments_config (dict, optional): Dictionary to override values of the instruments config.
        """
        self.exp_config = EXP_CONFIG.copy()  # important to copy so that the original config dict doesn't get modified
        self.instruments_config = INSTRUMENTS_CONFIG.copy()  # important to copy so that the original config dict doesn't get modified
        self.auto_set_exp_config()
        if FORCE_EXP_CONFIG is not None:
            update_nested_dict(self.exp_config, FORCE_EXP_CONFIG)  # first override from config
        if force_exp_config is not None:
            update_nested_dict(self.exp_config, force_exp_config)  # then from run kwargs
        self.auto_set_instruments_config()
        if FORCE_INSTRUMENTS_CONFIG is not None:
            update_nested_dict(self.instruments_config, FORCE_INSTRUMENTS_CONFIG)  # first override from config
        if force_instruments_config is not None:
            update_nested_dict(self.instruments_config, force_instruments_config)  # then from run kwargs
        self.qua_config = get_qua_config(self.exp_config, self.instruments_config)
        self.processed_config = self.process_config()  # does nothing unless redefined in child class

    def configure_and_run(self, force_exp_config=None, force_instruments_config=None,
                          simulate=False, do_fit=True, do_plot=True, do_save=True, validate='auto',
                          print_execution_report=False):
        """ Automatically configure and run the experiment.
        Args:
            force_exp_config (dict, optional): Dictionary to override values of the experiment config.
            force_instruments_config (dict, optional): Dictionary to override values of the instruments config.
            simulate (bool): Simulate the QUA program instead of running it.
            do_fit (bool): Whether to fit the data.
            do_plot (bool): Whether to plot the data.
            do_save (bool): Whether to save the data.
            validate (str): Whether to validate the data. Can take 'yes', 'no' or 'auto' (default), which relies on the
                `validate` method to determine if the measurements should be validated.
            print_execution_report` (bool): Whether to print the QM job execution report after it is completed.
        """
        self.configure(force_exp_config, force_instruments_config)
        self.run(
            simulate=simulate, do_fit=do_fit, do_plot=do_plot, do_save=do_save,
            validate=validate, print_execution_report=print_execution_report
        )

    def refit(self, show_figure=True, do_update=False, validate='auto'):
        """
        Redo the fit on an experiment that was already run.
        Args:
            show_figure (bool): Whether to show the figure.
            do_update (bool): Whether to update the saved data (HDF5, figure, and database) with the recomputed fit.
            validate (str): Whether to validate the data. Can take 'yes', 'no' or 'auto' (default), which relies on the
                `validate` method to determine if the measurements should be validated.
        """
        try:
            self.measured_db_params = self.fit()
        except RuntimeError as e:
            self.fit_params = {}  # ensure fit won't be plotted
            print("[!] Fit failed:", e)

        self.plot()

        if do_update:
            fig_path = make_figure_save_path(self.identifier, self.start_time)
            plt.gcf().savefig(fig_path)
            print("[+] Saved figure at", fig_path)

        if show_figure:
            plt.show()
        plt.close()

        if do_update:
            dict_to_update = {
                'fit_params': self.fit_params,
                'measured_db_params': self.measured_db_params,
            }
            update_dict_in_hdf5(dict_to_update, self.save_path, delete_first=True)
            print("[+] Updated saved data in", self.save_path,)
            self.delete_measured_params_from_db()
            match validate:
                case 'yes':
                    are_valid = True
                case 'no':
                    are_valid = False
                case 'auto':
                    are_valid = self.validate()
            self.save_measured_params_to_db(are_valid)


    def __str__(self):
        return f'{self.identifier}__{display_timestamp(self.start_time)}'
