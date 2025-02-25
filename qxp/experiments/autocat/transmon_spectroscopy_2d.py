import matplotlib.pyplot as plt
import numpy as np
from scipy import signal, optimize

from qm.qua import *
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.loops import from_array
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.plot import clean_axes_2d, adjust_axes_limits
from qxp.experiments.autocat.config import autoconfig
from qxp.utils.fit import fit_cosine, cosine_tmax_from_popt


class OneToneSpectroscopy(BaseQuaExperiment):
    experiment_name = 'transmon_spectroscopy_2d'
    description = """
        A two-tone spectroscopy of the readout transmon,
        where both transmon IF and pulse amplitudes are swept.
    """

    def __init__(self, i_freqs=None, rel_amps=None, pulse_type='pi', n_avg=2000, **kwargs):
        """
        Args:
            i_freqs: An array of the intermediate frequencies to use.
            pulse_type: The type of pulse ('pi' or 'saturation').
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.i_freqs = np.linspace(20, 100, 101) * u.MHz if i_freqs is None else i_freqs
        self.rel_amps = np.linspace(0, 2, 101) * u.MHz if rel_amps is None else rel_amps
        self.pulse_type = pulse_type
        self.n_avg = n_avg

    def auto_set_exp_config(self):
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)

        # set the transmon LO
        resonance_freq = self.exp_config['transmon']['resonance_freq']
        lo_freq = resonance_freq + (self.i_freqs[0] + self.i_freqs[-1]) // 2 + self.i_freqs[0]
        self.instruments_config['transmon_lo']['frequency'] = lo_freq

    def get_qua_program(self):
        """ QUA program """
        transmon_reset_time = self.exp_config['transmon']['reset_time']
        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the transmon frequency
            amp_factor = declare(fixed)

            i = declare(fixed)  # QUA variable for the measured 'I' quadrature
            q = declare(fixed)  # QUA variable for the measured 'Q' quadrature

            i_st = declare_stream()  # Stream for the 'I' quadrature
            q_st = declare_stream()  # Stream for the 'Q' quadrature

            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < self.n_avg, n + 1):
                with for_(*from_array(f, self.i_freqs)):
                    with for_(*from_array(amp_factor, self.rel_amps)):
                        update_frequency("transmon", f)

                        align()
                        if self.pulse_type == 'saturation':
                            play("transmon_const" * amp(amp_factor), "transmon")
                        elif self.pulse_type == 'pi':
                            play("transmon_pulse" * amp(amp_factor), "transmon")
                        else:
                            raise RuntimeError(f"Pulse type {self.pulse_type} not supported.")

                        align("transmon", "readout_resonator")
                        measure(
                            "readout",
                            "readout_resonator",
                            None,
                            demod.full("sin", i),
                            demod.full("cos", q),
                        )
                        wait(u.to_clock_cycles(transmon_reset_time),
                             "readout_resonator")  # Wait for the transmon to decay to the ground state

                        save(i, i_st)
                        save(q, q_st)

                    # Save the averaging iteration to get the progress bar
                    save(n, n_st)

            with stream_processing():
                i_st.buffer(len(self.i_freqs), len(self.rel_amps)).average().save("I")
                q_st.buffer(len(self.i_freqs), len(self.rel_amps)).average().save("Q")
                n_st.save("iteration")

        return prog

    def get_results(self, job):
        return fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")

    def get_data(self, results):
        i_rawdata, q_rawdata, iteration = results.fetch_all()
        readout_pulse_length = self.exp_config['transmon'][f'{self.pulse_type}_pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def live_plotting(self, job, results):
        lo = self.exp_config['transmon']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['transmon']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs
        abs_amps = self.exp_config['transmon'][f'{self.pulse_type}_pulse_amp'] * self.rel_amps

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        interrupt_on_close(fig, job)  # Interrupt the job when closing the figure
        fig.suptitle(f"Transmon spectroscopy - LO = {lo_freq / u.GHz} GHz")
        for ax in axs:
            ax.set_ylabel("Amplitude (V)")
        axs[1].set_xlabel("Transmon pulse frequency (MHz)")
        axs[0].set_title(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_title("Phase (rad)")
        fig.canvas.manager.set_window_title(f'{self.experiment_name}: {self.start_timestamp}')

        while results.is_processing():
            # Process the data
            data = self.get_data(results)
            iq_data = data['iq_data']
            amplitude = np.abs(iq_data)  # Amplitude
            phase = np.angle(iq_data)  # Phase
            unwrapped_phase = signal.detrend(np.unwrap(phase, axis=0), axis=0)

            # Plot the results
            clean_axes_2d(axs)
            axs[0].pcolorpesh(r_freqs / u.MHz, abs_amps, amplitude)
            axs[1].pcolorpesh(r_freqs / u.MHz, abs_amps, unwrapped_phase)

            adjust_axes_limits(axs)
            plt.pause(0.1)
            progress_counter(data['iteration'], self.n_avg, start_time=results.get_start_time())  # progress bar

    def plot(self):
        lo = self.exp_config['transmon']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['transmon']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs
        abs_amps = self.exp_config['transmon'][f'{self.pulse_type}_pulse_amp'] * self.rel_amps

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        fig.suptitle(f"Transmon spectroscopy")
        for ax in axs:
            ax.set_ylabel("amplitude (V)")
        axs[1].set_xlabel("frequency (MHz)")
        axs[0].set_title(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_title("Phase (rad)")

        iq_data = self.data['iq_data']
        amplitude = np.abs(iq_data)  # Amplitude
        phase = np.angle(iq_data)  # Phase
        unwrapped_phase = signal.detrend(np.unwrap(phase, axis=0), axis=0)

        # Plot the results
        axs[0].pcolorpesh(r_freqs / u.MHz, abs_amps, amplitude.T)
        axs[1].pcolorpesh(r_freqs / u.MHz, abs_amps, unwrapped_phase.T)
        return fig

    def fit(self, fig=None):
        lo = self.exp_config['transmon']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['transmon']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs
        abs_amps = self.exp_config['transmon'][f'{self.pulse_type}_pulse_amp'] * self.rel_amps
        transmon_pulse_length = self.exp_config['transmon'][f'{self.pulse_type}_pulse_length']

        fig, axs = plt.subplots(2, 1, tight_layout=True, figsize=(4, 8))
        axs[0].set_xlabel('amplitude (V)')
        axs[0].set_ylabel('frequency (MHz)')

        amplitude = np.abs(self.data['iq_data'])  # Amplitude
        im = axs[0].pcolorpesh(r_freqs / u.MHz, abs_amps, amplitude.T)
        fig.colorbar(im, ax=axs[0])

        freq_index = np.argmax(np.mean(np.abs(amplitude - amplitude[0, 0]), axis=1))  # TODO improve (IQ distance?))
        axs[0].axvline(r_freqs[freq_index] / u.MHz, linestyle='--', color='black')

        rabi_oscillations = amplitude[freq_index, :]
        axs[1].plot(abs_amps, rabi_oscillations, '-.', label='data')

        p0 = [1e-3, 1e-2, 0, 5e-4]
        popt, pcov = optimize.curve_fit(fit_cosine, abs_amps, rabi_oscillations, p0=p0)
        axs[1].plot(abs_amps, fit_cosine(abs_amps, *popt), '-', label='fit')
        pi_pulse_amp = cosine_tmax_from_popt(popt)
        axs[1].axvline(pi_pulse_amp, linestyle='--', color='black')
        axs[1].set_xlabel('amplitude')
        axs[1].set_ylabel('IQ distance')
        axs[1].legend()

        transmon_resonance_frequency = r_freqs[freq_index]

        print(f"Transmon frequency: {transmon_resonance_frequency} GHz")
        print(f"Pi pulse amplitude @ {transmon_pulse_length} ns: {pi_pulse_amp:.05f}")

        if fig is not None:
            axs = fig.axes
            axs[0].plot(r_freqs, ..., ".", label="Fit")
            axs[0].legend()

        return {
            'transmon_resonance_frequency': transmon_resonance_frequency,
            'transmon_pi_pulse_amplitude': ...
        }
