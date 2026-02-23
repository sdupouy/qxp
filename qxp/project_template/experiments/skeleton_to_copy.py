from dataclasses import dataclass

import matplotlib.pyplot as plt
from qm.qua import *

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.experiment import copy_default
from qxp.utils.units import units as u
from qxp.utils.qua import demod2volts
from qxp.utils.plot import clean_axes, adjust_axes_limits


@dataclass
class SkeletonExperiment(BaseQuaExperiment):
    """
    You should copy this file and use it as a basis for a QUA experiment class.

    Prerequisites:
        - Having measured ...
    """
    identifier = 'skeleton_experiment'
    display_name = 'Skeleton experiment'

    # Define experiment parameters here:
    parameter: int = 0  # will be accessible as self.parameter
    parameter2: np.ndarray = copy_default(np.arange(10))  # copy_default is used to avoid modifying the original array

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        ...  # use an autoconfig function in qxp.experiments.utils.autoconfig

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        ...  # use an autoconfig function in qxp.experiments.utils.autoconfig

    def process_config(self):
        """ (Optionnal) """
        processed_config = {
            '...': ...,
        }
        return processed_config

    def pre_run(self, qm):
        """ (Optionnal) """
        pre_run_data = ...
        return pre_run_data

    def get_qua_program(self):
        """ QUA program """
        with program() as prog:
            ...

            with stream_processing():
                ...

        return prog

    def manage_job_pauses(self, job):
        """ (Optionnal) """
        instrument = get_instrument_by_name(..., self.instruments_config)

        # Example:
        for power in ...:
            instrument.set_power_dbm(power_dbm=power)
            # Resume the QUA program (escape the 'pause' statement)
            job.resume()
            wait_until_job_is_paused(job)
        job.halt()  # otherwise it remains in paused state

    def get_data(self, result_handles):
        # Example:
        i_rawdata = result_handles.get("I").fetch_all()
        q_rawdata = result_handles.get("Q").fetch_all()
        iteration = result_handles.get("iteration").fetch_all()

        readout_pulse_length = self.exp_config['readout']['ro_pulse_length']
        iq_data = demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def process_data(self):
        """ (Optionnal) """
        processed_data = {
            '...': ...,
        }
        return processed_data

    def progress(self):
        """ (Optionnal) """
        return self.data['iteration'] / self.n_avg * 100

    def fit(self):
        # DO THE FIT
        ...
        self.fit_params = ...  # to be used by self.plot

        # PRINT FITTED PARAMETERS
        ...

        return {
            # To be saved in database
            # KEY: VALUE,
        }

    def validate(self):
        ...
        return {
            'parameter1': True,
            'parameter2': False,
        }

    def initialize_plot(self):
        fig, axs = plt.subplots()
        ...
        return {
            # Updatables to be updated in self.update_plot
            # KEY: VALUE,
        }

    def update_plot(self, updatables):
        updatables['lines1'].set_data(...)
