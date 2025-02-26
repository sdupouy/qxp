"""
This file is a skeleton for an experiment class, to copy and fill!
"""

import matplotlib.pyplot as plt

from qm.qua import *
from qualang_tools.results import progress_counter
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.plot import clean_axes, adjust_axes_limits


class SkeletonExperiment(BaseQuaExperiment):
    experiment_name = 'skeleton_experiment'
    description = """Short description."""

    def __init__(self, param, **kwargs):
        """
        Args:
            param: An example parameter.
        """
        super().__init__(**kwargs)
        # DEFINE YOUR EXPERIMENT PARAMETERS
        # self.param = param

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        ...  # use an autoconfig function in qxp.experiments.your_project.config.autoconfig

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        ...  # use an autoconfig function in qxp.experiments.your_project.config.autoconfig

    def get_qua_program(self):
        """ QUA program """
        with program() as prog:
            ...

            with stream_processing():
                ...

        return prog

    def get_data(self, result_handles):
        i_rawdata = result_handles.get("I").fetch_all()
        q_rawdata = result_handles.get("Q").fetch_all()
        iteration = result_handles.get("iteration").fetch_all()

        readout_pulse_length = self.exp_config['readout']['pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def live_plotting(self, job, result_handles):
        fig, axs = plt.subplots()
        interrupt_on_close(fig, job)  # Interrupt the job when closing the figure

        # SET THE TITLE AND LABELS
        ...
        fig.canvas.manager.set_window_title(f'{self.experiment_name}: {self.start_timestamp}')

        while result_handles.is_processing():
            # Process the data
            data = self.get_data(result_handles)
            ...

            # Plot the results
            clean_axes(axs)
            ...

            adjust_axes_limits(axs)
            plt.pause(0.1)
            progress_counter(data['iteration'], self.n_avg)  # progress bar

    def fit(self):
        # DO THE FIT
        ...
        self.fit_params = ...  # to be used by self.plot

        # PRINT FITTED PARAMETERS
        ...

        return {
            # KEY: VALUE,
        }

    def plot(self):
        fig, axs = plt.subplots()
        ...
        return fig
