import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from resonator import reflection, background

from qm.qua import *
from qualang_tools.results import progress_counter
from qualang_tools.loops import from_array
from qualang_tools.units import unit
from qualang_tools.plot import interrupt_on_close
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.utils.plot import clean_axes, adjust_axes_limits
from qxp.experiments.autocat.config import autoconfig


class RoResonatorSpectroscopy(BaseQuaExperiment):
    # TODO write a docstring!

    identifier = 'ro_resonator_spectroscopy'
    display_name = 'Readout resonator spectroscopy (1-tone)'

    def __init__(self, i_freqs=None, n_avg=2000, excite_transmon=False, **kwargs):
        """
        Args:
            i_freqs: An array of the intermediate frequencies to use, in Hertz.
            n_avg: The averaging.
            excite_transmon: Whether to excite the transmon before readout.
        """
        super().__init__(**kwargs)
        self.i_freqs = np.linspace(20, 100, 1001) * u.MHz if i_freqs is None else i_freqs
        self.n_avg = n_avg
        self.excite_transmon = excite_transmon

    def auto_set_exp_config(self):
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)
        
        # set the readout resonator LO
        resonance_freq = self.exp_config['ro_resonator']['resonance_freq']
        lo_freq = resonance_freq + (self.i_freqs[0] + self.i_freqs[-1]) // 2 + self.i_freqs[0]
        self.instruments_config['ro_resonator_lo']['frequency'] = lo_freq

    def get_qua_program(self):
        """ QUA program """
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']

        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            f = declare(int)  # QUA variable for the readout frequency
            i = declare(fixed)  # QUA variable for the measured 'I' quadrature
            q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            i_st = declare_stream()  # Stream for the 'I' quadrature
            q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < self.n_avg, n + 1):
                with for_(*from_array(f, self.i_freqs)):
                    update_frequency("ro_resonator", f)

                    if self.excite_transmon:
                        play("transmon_pulse", "transmon")
                        align()

                    measure(
                        "readout",
                        "ro_resonator",
                        None,
                        demod.full("sin", i),
                        demod.full("cos", q),
                    )
                    wait(u.to_clock_cycles(ro_reset_time), "ro_resonator")

                    save(i, i_st)
                    save(q, q_st)

                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
                i_st.buffer(len(self.i_freqs)).average().save("I")
                q_st.buffer(len(self.i_freqs)).average().save("Q")
                n_st.save("iteration")

        return prog

    def get_data(self, result_handles):
        i_rawdata = result_handles.get("I").fetch_all()
        q_rawdata = result_handles.get("Q").fetch_all()
        iteration = result_handles.get("iteration").fetch_all()

        readout_pulse_length = self.exp_config['ro_resonator']['ro_pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def live_plotting(self, job):
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        interrupt_on_close(fig, job)  # Interrupt the job when closing the figure

        fig.suptitle(f"Resonator spectroscopy - LO = {lo_freq / u.GHz} GHz")
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
            plt.pause(1)
            progress_counter(data['iteration'], self.n_avg)  # progress bar

    def fit(self):
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs

        background_model = background.MagnitudeSlopeOffsetPhaseDelay()
        resonator = reflection.LinearReflectionFitter(
            frequency=r_freqs,
            data=self.data['iq_data'],
            background_model=background_model
        )

        self.fit_params = {
            'resonator_fit': resonator.evaluate_fit(resonator.frequency)
        }

        print(f"Resonance frequency = {resonator.resonance_frequency / u.GHz:.3f} GHz")
        print(f"Kappa_coupling = {resonator.coupling_energy_decay_rate / u.MHz:.3f} MHz")
        print(f"Kappa_internal = {resonator.internal_energy_decay_rate / u.MHz:.3f} MHz")

        return {
            'ro_resonator_resonance_frequency': resonator.resonance_frequency,
            'ro_resonator_kappa_coupling': resonator.coupling_energy_decay_rate,
            'ro_resonator_kappa_internal': resonator.internal_energy_decay_rate,
        }

    def plot(self):
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        r_freqs = lo_freq + sideband * self.i_freqs

        fig, axs = plt.subplots(2, 1, sharex=True, tight_layout=True, figsize=(6, 8))
        fig.suptitle(f"Resonator spectroscopy")
        axs[0].set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ (V)")
        axs[1].set_ylabel("phase (rad)")
        axs[1].set_xlabel("frequency (MHz)")

        iq_data = self.data['iq_data']
        amplitude = np.abs(iq_data)  # Amplitude
        phase = np.angle(iq_data)  # Phase
        unwrapped_phase = signal.detrend(np.unwrap(phase))

        # Plot results
        axs[0].plot(r_freqs / u.MHz, amplitude, ".", label="data")
        axs[1].plot(r_freqs / u.MHz, unwrapped_phase, ".", label="data")

        if self.fit_params:
            fit = self.fit_params['resonator_fit']
            axs[0].plot(r_freqs / u.MHz, np.abs(fit), label="fit")
            axs[1].plot(r_freqs / u.MHz, np.angle(fit), label="fit")
            axs[0].legend()
            axs[1].legend()

        return fig
