"""
This file is a skeleton for an experiment class, to copy and fill!
"""

import matplotlib.pyplot as plt

from qm.qua import *
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.plot import clean_axes, adjust_axes_limits


class SkeletonExperiment(BaseQuaExperiment):
    experiment_name = 'skeleton_experiment'

    def __init__(self, param, **kwargs):
        """
        Args:
            param: An example parameter.
        """
        super().__init__(**kwargs)
        # DEFINE YOUR EXPERIMENT PARAMETERS
        # self.param = param

    def set_default_parameters(self):
        pass

    def get_qua_program(self):
        """ QUA program """
        with program() as prog:
            ...

            with stream_processing():
                ...

        return prog

    def get_results(self, job):
        return fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")

    def get_data(self, results):
        i_rawdata, q_rawdata, iteration = results.fetch_all()
        readout_pulse_length = self.config_params['readout']['pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def live_plotting(self, job, results):
        fig, axs = plt.subplots()
        interrupt_on_close(fig, job)  # Interrupt the job when closing the figure

        # SET THE TITLE AND LABELS
        ...
        fig.canvas.manager.set_window_title(f'{self.experiment_name}: {self.start_timestamp}')

        while results.is_processing():
            # Process the data
            data = self.get_data(results)
            ...

            # Plot the results
            clean_axes(axs)
            ...

            adjust_axes_limits(axs)
            plt.pause(0.1)
            progress_counter(data['iteration'], self.n_avg, start_time=results.get_start_time())  # progress bar

    def plot(self):
        fig, axs = plt.subplots()
        ...
        return fig

    def fit(self, fig=None):
        # DO THE FIT
        ...

        # PRINT FITTED PARAMETERS
        ...

        if fig is not None:
            axs = fig.axes
            # PLOT THE FIT
            ...

        return {
            # KEY: VALUE,
        }
