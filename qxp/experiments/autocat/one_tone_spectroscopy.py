import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from qm.qua import *
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.loops import from_array
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
from qualang_tools.plot.fitting import Fit
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.plot import clean_axes, adjust_axes_limits
from qxp.experiments.autocat.config import autoconfig


class OneToneSpectroscopy(BaseQuaExperiment):
    experiment_name = 'one_tone_spectroscopy'

    def __init__(self, i_freq=None, n_avg=2000, excite_transmon=False, **kwargs):
        """
        Args:
            i_freq: An array of the intermediate frequencies to use.
            n_avg: The averaging.
            excite_transmon: Whether to excite the transmon before readout.
        """
        super().__init__(**kwargs)
        self.i_freq = np.linspace(20, 100, 1001) * u.MHz if i_freq is None else i_freq
        self.n_avg = n_avg
        self.excite_transmon = excite_transmon

    def auto_set_exp_config(self):
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)
        
        # set the readout resonator LO
        resonance_freq = self.exp_config['ro_resonator']['resonance_freq']
        lo_freq = resonance_freq + (self.i_freq[0] + self.i_freq[-1]) // 2 + self.i_freq[0]
        self.instruments_config['ro_resonator_lo']['frequency'] = lo_freq

    def get_qua_program(self):
        """ QUA program """
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']
        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the readout frequency
            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < self.n_avg, n + 1):
                with for_(*from_array(f, self.i_freq)):
                    update_frequency("readout_resonator", f)

                    if self.excite_transmon:
                        play("transmon_pulse", "transmon")
                        align()

                    measure(
                        "readout",
                        "readout_resonator",
                        None,
                        demod.full("sin", I),
                        demod.full("cos", Q),
                    )
                    wait(u.to_clock_cycles(ro_reset_time), "readout_resonator")

                    save(I, I_st)
                    save(Q, Q_st)

                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
                I_st.buffer(len(self.i_freq)).average().save("I")
                Q_st.buffer(len(self.i_freq)).average().save("Q")
                n_st.save("iteration")

        return prog

    def get_results(self, job):
        return fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")

    def get_data(self, results):
        i_rawdata, q_rawdata, iteration = results.fetch_all()
        readout_pulse_length = self.exp_config['ro_resonator']['pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def live_plotting(self, job, results):
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        r_freq = lo_freq + sideband * self.i_freq

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        interrupt_on_close(fig, job)  # Interrupt the job when closing the figure

        fig.suptitle(f"Resonator spectroscopy - LO = {lo_freq / u.GHz} GHz")
        axs[0].set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_ylabel("Phase (rad)")
        axs[1].set_xlabel("Readout pulse frequency (Hz)")
        fig.canvas.manager.set_window_title(f'{self.experiment_name}: {self.start_timestamp}')

        while results.is_processing():
            # Process the data
            data = self.get_data(results)
            iq_data = data['iq_data']
            amplitude = np.abs(iq_data)  # Amplitude
            phase = np.angle(iq_data)  # Phase
            unwrapped_phase = signal.detrend(np.unwrap(phase))

            # Plot the results
            clean_axes(axs)
            axs[0].plot(r_freq, amplitude, ".")
            axs[1].plot(r_freq, unwrapped_phase, ".")

            adjust_axes_limits(axs)
            plt.pause(0.1)
            progress_counter(data['iteration'], self.n_avg, start_time=results.get_start_time())  # progress bar

    def plot(self):
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        r_freq = (lo_freq + sideband * self.i_freq) / u.MHz

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        fig.suptitle(f"Resonator spectroscopy")
        axs[0].set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_ylabel("Phase (rad)")
        axs[1].set_xlabel("Readout pulse frequency (MHz)")

        iq_data = self.data['iq_data']
        amplitude = np.abs(iq_data)  # Amplitude
        phase = np.angle(iq_data)  # Phase
        unwrapped_phase = signal.detrend(np.unwrap(phase))

        # Plot results
        axs[0].plot(r_freq, amplitude, ".", label="Data")
        axs[1].plot(r_freq, unwrapped_phase, ".")
        return fig

    def fit(self, fig=None):
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        r_freq = lo_freq + sideband * self.i_freq

        fit = Fit().reflection_resonator_spectroscopy(r_freq, np.abs(self.data['iq_data']))

        print(f"Resonance frequency = {fit['f'][0] / u.GHz:.3f} GHz")
        print(f"Kappa = {fit['k'][0] / u.MHz:.3f} MHz")

        if fig is not None:
            axs = fig.axes
            axs[0].plot(r_freq, fit['fit_func'](r_freq), ".", label="Fit")
            axs[0].legend()

        return {
            'readout_resonator_resonance_frequency': fit['f'][0],
            'readout_resonator_kappa': fit['k'][0],
        }
