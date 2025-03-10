import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter

from qm.qua import *
from qualang_tools.units import unit
u = unit()

from qxp.experiments.autocat.config import autoconfig
from qxp.experiments.base_experiment import BaseQuaExperiment


class TimeOfFlight(BaseQuaExperiment):
    # TODO: write a docstring

    identifier = 'time_of_flight'
    display_name = 'Time of flight'

    def __init__(self, n_avg=10000, **kwargs):
        """
        Args:
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.n_avg = n_avg

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        autoconfig.auto_set_exp_config(self.exp_config)
        self.exp_config['ro_resonator']['time_of_flight'] = 24  # minimum allowed

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)

    def get_qua_program(self):
        """ QUA program """
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']
        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            adc_st = declare_stream(adc_trace=True)  # The stream to store the raw ADC trace

            with for_(n, 0, n < self.n_avg, n + 1):
                # Reset the phase of the digital oscillator associated to the resonator element. Needed to average the cosine signal.
                reset_phase("ro_resonator")
                # Sends the readout pulse and stores the raw ADC traces in the stream called "adc_st"
                measure("readout", "ro_resonator", adc_st)
                # Wait for the resonator to deplete
                wait(u.to_clock_cycles(ro_reset_time), "ro_resonator")

            with stream_processing():
                # Will save average:
                adc_st.input1().average().save("adc1")
                # Will save only last run:
                adc_st.input1().save("adc1_single_run")

        return prog

    def get_data(self, result_handles):
        adc1 = result_handles.get("adc1").fetch_all()
        adc1_single_run = result_handles.get("adc1_single_run").fetch_all()

        adc1 = u.raw2volts(adc1)
        adc1_single_run = u.raw2volts(adc1_single_run)
        data = {
            'adc1': adc1,
            'adc1_single_run': adc1_single_run,
        }
        return data

    def fit(self):
        adc1 = self.data['adc1']
        adc1_unbiased = adc1 - np.mean(adc1)
        # Detect the arrival of the readout signal
        filtered_signal = savgol_filter(np.abs(adc1_unbiased), 11, 3)
        th = (np.mean(filtered_signal[:100]) + np.mean(filtered_signal[:-100])) / 2
        delay = np.argmax(filtered_signal > th)
        delay = np.round(delay / 4) * 4  # Find the closest multiple integer of 4ns
        self.fit_params['delay'] = delay
        time_of_flight = delay + self.exp_config['ro_resonator']['time_of_flight']
        print(f"Time of flight = {time_of_flight} ns")

        return {
            'time_of_flight': time_of_flight,
        }

    def plot(self):
        fig, axs = plt.subplots(2, 1)
        axs[0].set_ylabel('Amplitude (V)')
        axs[0].set_title('Single trace')
        axs[1].set_xlabel('Time (ns)')
        axs[1].set_ylabel('Amplitude (V)')
        axs[1].set_title('Averaged trace')

        axs[0].plot(self.data["adc1_single_run"])
        axs[1].plot(self.data["adc1"])

        if self.fit_params:
            axs[1].axvline(self.fit_params['delay'], linestyle='--', color='black')
        return fig
