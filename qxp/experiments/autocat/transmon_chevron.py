import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from qm.qua import *
from qualang_tools.results import progress_counter
from qualang_tools.loops import from_array
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.plot import clean_axes, adjust_axes_limits
from qxp.experiments.autocat.config import autoconfig


class TransmonChevron(BaseQuaExperiment):
    """
    TRANSMON CHEVRON
    This sequence involves sending a tone to the transmon with a 2D sweep in frequency and amplitude, and a readout
    is done at each step.

    Prerequisites:
        - Having measured the readout resonator frequency.
    """
    identifier = 'transmon_chevron'
    display_name = 'Transmon chevron'

    def __init__(self, i_freqs=None, amps=None, pulse_type='saturation', n_avg=2000, **kwargs):
        """
        Args:
            i_freqs: An array of the intermediate frequencies to use.
            amps: The relative amplitudes.
            pulse_type: The type of pulse ('pi' or 'saturation').
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.i_freqs = np.linspace(20, 100, 1001) * u.MHz if i_freqs is None else i_freqs
        self.amps = np.linspace(0, 2, 1001) if amps is None else amps
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
            a = declare(int)  # QUA variable for the relative amplitude
            f = declare(int)  # QUA variable for the transmon frequency
            i = declare(fixed)  # QUA variable for the measured 'I' quadrature
            q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            i_st = declare_stream()  # Stream for the 'I' quadrature
            q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < self.n_avg, n + 1):
                with for_(*from_array(f, self.i_freqs)):
                    update_frequency("transmon", f)
                    with for_(*from_array(a, self.amps)):
                        align()
                        if self.pulse_type == 'saturation':
                            play("transmon_saturation" * amp(a), "transmon")
                        elif self.pulse_type == 'pi':
                            play("transmon_pi" * amp(a), "transmon")

                        align("transmon", "ro_resonator")
                        measure(
                            "readout",
                            "ro_resonator",
                            None,
                            demod.full("sin", i),
                            demod.full("cos", q),
                        )
                        # Wait for the transmon to decay to the ground state
                        wait(u.to_clock_cycles(transmon_reset_time),"ro_resonator")

                        save(i, i_st)
                        save(q, q_st)

                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                i_st.buffer(len(self.i_freqs), len(self.amps)).average().save("I")
                q_st.buffer(len(self.i_freqs), len(self.amps)).average().save("Q")
                n_st.save("iteration")

        return prog

    def get_data(self, result_handles):
        i_rawdata = result_handles.get("I").fetch_all()
        q_rawdata = result_handles.get("Q").fetch_all()
        iteration = result_handles.get("iteration").fetch_all()
        readout_pulse_length = self.exp_config['transmon'][f'{self.pulse_type}_pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def live_plotting(self, job):
        # TODO
        lo = self.exp_config['transmon']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['transmon']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        interrupt_on_close(fig, job)  # Interrupt the job when closing the figure

        fig.suptitle(f"Transmon spectroscopy - LO = {lo_freq / u.GHz} GHz")
        axs[0].set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_ylabel("phase (rad)")
        axs[1].set_xlabel("frequency (MHz)")
        fig.canvas.manager.set_window_title(f'{self.identifier}: {self.start_timestamp}')

        while job.result_handles.is_processing():
            # Process the data
            data = self.get_data(job.result_handles)
            iq_data = data['iq_data']
            amplitude = np.abs(iq_data)  # Amplitude
            phase = np.angle(iq_data)  # Phase
            unwrapped_phase = signal.detrend(np.unwrap(phase))

            # Plot the results
            clean_axes(axs)
            axs[0].plot(r_freqs / u.MHz, amplitude, ".")
            axs[1].plot(r_freqs / u.MHz, unwrapped_phase, ".")

            adjust_axes_limits(axs)
            plt.pause(0.1)
            progress_counter(data['iteration'], self.n_avg)  # progress bar

    def fit(self):
        # TODO
        lo = self.exp_config['transmon']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['transmon']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs

        raise NotImplementedError  # TODO

        print(f"Transmon resonance frequency = {fit['f'][0] / u.GHz:.3f} GHz")

        return {
            'transmon_resonance_freq': fit['f'][0],
        }

    def plot(self):
        # TODO
        lo = self.exp_config['transmon']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['transmon']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        fig.suptitle(f"Transmon spectroscopy")
        axs[0].set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_ylabel("phase (rad)")
        axs[1].set_xlabel("frequency (MHz)")

        iq_data = self.data['iq_data']
        amplitude = np.abs(iq_data)  # Amplitude
        phase = np.angle(iq_data)  # Phase
        unwrapped_phase = signal.detrend(np.unwrap(phase))

        # Plot results
        axs[0].plot(r_freqs / u.MHz, amplitude, ".", label="Data")
        axs[1].plot(r_freqs / u.MHz, unwrapped_phase, ".")
        return fig
