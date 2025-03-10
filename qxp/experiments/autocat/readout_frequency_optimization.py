import matplotlib.pyplot as plt
import numpy as np

from qm.qua import *
from qualang_tools.units import unit
from qualang_tools.loops import from_array
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.experiments.autocat.config import autoconfig
from qxp.utils.qua import result_handles_to_data_dict


class ReadoutFrequencyOptimization(BaseQuaExperiment):
    """
    READOUT OPTIMISATION: FREQUENCY
    This sequence involves measuring the state of the resonator in two scenarios: first, after thermalization
    (with the qubit in the |g> state) and then after applying a pi pulse to the qubit (transitioning the qubit to the
    |e> state). This is done while varying the readout frequency.
    The average I & Q quadratures for the qubit states |g> and |e>, along with their variances, are extracted to
    determine the Signal-to-Noise Ratio (SNR). The readout frequency that yields the highest SNR is selected as the
    optimal choice.

    Prerequisites:
        - Having measured the readout resonator frequency.
        - Having calibrated the qubit pi pulse.
    """
    identifier = 'readout_frequency_optimization'
    display_name = 'Readout frequency optimization'

    def __init__(self, dfs=None, n_avg=300, **kwargs):
        """
        Args:
            dfs: The frequency delta array from the readout resonator IF, in Hertz.
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.dfs = np.linspace(-10, 10, 1001) * u.MHz if dfs is None else dfs
        self.n_avg = n_avg

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)

    def get_qua_program(self):
        """ QUA program """
        f_steps = len(self.dfs)
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']
        ro_resonator_if = self.exp_config['ro_resonator']['i_freq']

        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            df = declare(int)  # QUA variable for the readout frequency
            I_g = declare(fixed)  # QUA variable for the 'I' quadrature when the qubit is in |g>
            Q_g = declare(fixed)  # QUA variable for the 'Q' quadrature when the qubit is in |g>
            Ig_st = declare_stream()
            Qg_st = declare_stream()
            I_e = declare(fixed)  # QUA variable for the 'I' quadrature when the qubit is in |e>
            Q_e = declare(fixed)  # QUA variable for the 'Q' quadrature when the qubit is in |e>
            Ie_st = declare_stream()
            Qe_st = declare_stream()
            n_st = declare_stream()

            with for_(n, 0, n < self.n_avg, n + 1):
                with for_(*from_array(df, self.dfs)):
                    # Update the frequency of the digital oscillator linked to the resonator element
                    update_frequency("ro_resonator", df + ro_resonator_if)
                    # Measure the state of the resonator
                    measure(
                        "readout",
                        "ro_resonator",
                        None,
                        demod.full("sin", I_g),
                        demod.full("cos", Q_g),
                    )
                    # Wait for the qubit to decay to the ground state
                    wait(u.to_clock_cycles(ro_reset_time), "ro_resonator")
                    # Save the 'I_e' & 'Q_e' quadratures to their respective streams
                    save(I_g, Ig_st)
                    save(Q_g, Qg_st)

                    align()  # global align
                    # Play the pi gate to put the qubit in the excited state
                    play("transmon_pi", "transmon")
                    # Align the two elements to measure after playing the qubit pulse.
                    align("transmon", "ro_resonator")
                    # Measure the state of the resonator
                    measure(
                        "readout",
                        "ro_resonator",
                        None,
                        demod.full("sin", I_e),
                        demod.full("cos", Q_e),
                    )
                    # Wait for the qubit to decay to the ground state
                    wait(u.to_clock_cycles(ro_reset_time), "ro_resonator")
                    # Save the 'I_e' & 'Q_e' quadratures to their respective streams
                    save(I_e, Ie_st)
                    save(Q_e, Qe_st)
                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                n_st.save("iteration")
                # mean values
                Ig_st.buffer(f_steps).average().save("Ig_avg")
                Qg_st.buffer(f_steps).average().save("Qg_avg")
                Ie_st.buffer(f_steps).average().save("Ie_avg")
                Qe_st.buffer(f_steps).average().save("Qe_avg")
                # variances to get the SNR
                (
                        ((Ig_st.buffer(f_steps) * Ig_st.buffer(f_steps)).average())
                        - (Ig_st.buffer(f_steps).average() * Ig_st.buffer(f_steps).average())
                ).save("Ig_var")
                (
                        ((Qg_st.buffer(f_steps) * Qg_st.buffer(f_steps)).average())
                        - (Qg_st.buffer(f_steps).average() * Qg_st.buffer(f_steps).average())
                ).save("Qg_var")
                (
                        ((Ie_st.buffer(f_steps) * Ie_st.buffer(f_steps)).average())
                        - (Ie_st.buffer(f_steps).average() * Ie_st.buffer(f_steps).average())
                ).save("Ie_var")
                (
                        ((Qe_st.buffer(f_steps) * Qe_st.buffer(f_steps)).average())
                        - (Qe_st.buffer(f_steps).average() * Qe_st.buffer(f_steps).average())
                ).save("Qe_var")

        return prog

    def get_data(self, result_handles):
        data = result_handles_to_data_dict(result_handles)
        data['Z'] = (data['Ie_avg'] - data['Ig_avg']) + 1j * (data['Qe_avg'] - data['Qg_avg'])
        data['var'] = (data['Ig_var'] + data['Qg_var'] + data['Ie_var'] + data['Qe_var']) / 4
        data['SNR'] = ((np.abs(data['Z'])) ** 2) / (2 * data['var'])
        return data

    def fit(self):
        i_freq = self.exp_config['ro_resonator']['i_freq']
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']

        opti_freq = (self.dfs[np.argmax(self.data['SNR'])] + i_freq) * sideband + lo_freq
        print(f"The optimal readout frequency is {opti_freq} Hz (SNR={np.max(self.data['SNR'])})")

        return {
            'ro_pulse_freq': opti_freq,
        }

    def plot(self):
        i_freq = self.exp_config['ro_resonator']['i_freq']
        lo = self.exp_config['ro_resonator']['lo']
        lo_freq = self.instruments_config[lo]['frequency']
        sideband = self.exp_config['ro_resonator']['sideband']
        freqs = (self.dfs + i_freq) * sideband + lo_freq

        fig, ax = plt.subplots()
        ax.plot(freqs * u.MHz, self.data['SNR'])
        if 'ro_pulse_freq' in self.measured_db_params:
            ax.axvline(self.measured_db_params['ro_pulse_freq'] * u.MHz)
        ax.set_title(f"Readout frequency optimization (LO = {lo_freq * u.MHz:.03f} MHz)")
        ax.set_xlabel("Readout frequency detuning (MHz)")
        ax.set_ylabel("SNR")
        return fig
