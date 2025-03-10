import matplotlib.pyplot as plt
import numpy as np

from qm.qua import *
from qualang_tools.units import unit
from qualang_tools.loops import from_array
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.experiments.autocat.config import autoconfig
from qxp.utils.qua import result_handles_to_data_dict


class ReadoutAmplitudeOptimization(BaseQuaExperiment):
    """
    READOUT OPTIMISATION: AMPLITUDE
    The sequence consists in measuring the state of the resonator after thermalization (qubit in |g>) and after
    playing a pi pulse to the qubit (qubit in |e>) successively while sweeping the readout amplitude.
    The 'I' & 'Q' quadratures when the qubit is in |g> and |e> are extracted to derive the SNR.
    The optimal readout amplitude is chosen as to maximize the SNR.

    Prerequisites:
        - Having calibrated the qubit pi pulse.
        - Having calibrated the readout frequency.
    """
    identifier = 'readout_amplitude_optimization'
    display_name = 'Readout amplitude optimization'

    def __init__(self, amps=None, n_avg=300, **kwargs):
        """
        Args:
            amps: The relative amplitudes.
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.amps = np.linspace(0, 2, 1001) if amps is None else amps
        self.n_avg = n_avg

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)

    def get_qua_program(self):
        """ QUA program """
        amp_steps = len(self.amps)
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']

        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            a = declare(int)  # QUA variable for the readout relative amplitude
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
                with for_(*from_array(a, self.amps)):
                    # Measure the state of the resonator
                    measure(
                        "readout" * amp(a),
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
                        "readout" * amp(a),
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
                Ig_st.buffer(amp_steps).average().save("Ig_avg")
                Qg_st.buffer(amp_steps).average().save("Qg_avg")
                Ie_st.buffer(amp_steps).average().save("Ie_avg")
                Qe_st.buffer(amp_steps).average().save("Qe_avg")
                # variances to get the SNR
                (
                        ((Ig_st.buffer(amp_steps) * Ig_st.buffer(amp_steps)).average())
                        - (Ig_st.buffer(amp_steps).average() * Ig_st.buffer(amp_steps).average())
                ).save("Ig_var")
                (
                        ((Qg_st.buffer(amp_steps) * Qg_st.buffer(amp_steps)).average())
                        - (Qg_st.buffer(amp_steps).average() * Qg_st.buffer(amp_steps).average())
                ).save("Qg_var")
                (
                        ((Ie_st.buffer(amp_steps) * Ie_st.buffer(amp_steps)).average())
                        - (Ie_st.buffer(amp_steps).average() * Ie_st.buffer(amp_steps).average())
                ).save("Ie_var")
                (
                        ((Qe_st.buffer(amp_steps) * Qe_st.buffer(amp_steps)).average())
                        - (Qe_st.buffer(amp_steps).average() * Qe_st.buffer(amp_steps).average())
                ).save("Qe_var")

        return prog

    def get_data(self, result_handles):
        data = result_handles_to_data_dict(result_handles)
        data['Z'] = (data['Ie_avg'] - data['Ig_avg']) + 1j * (data['Qe_avg'] - data['Qg_avg'])
        data['var'] = (data['Ig_var'] + data['Qg_var'] + data['Ie_var'] + data['Qe_var']) / 4
        data['SNR'] = ((np.abs(data['Z'])) ** 2) / (2 * data['var'])
        return data

    def fit(self):
        start_amp = self.exp_config['ro_resonator']['ro_pulse_amp']

        opti_amp = self.amps[np.argmax(self.data['SNR'])] * start_amp
        print(f"The optimal readout amplitude is {opti_amp} V")

        return {
            'ro_pulse_amp': opti_amp,
        }

    def plot(self):
        start_amp = self.exp_config['ro_resonator']['ro_pulse_amp']
        amps = self.amps * start_amp  # absolute (V)

        fig, ax = plt.subplots()
        ax.plot(amps, self.data['SNR'])
        if 'ro_pulse_amp' in self.measured_db_params:
            ax.axvline(self.measured_db_params['ro_pulse_amp'])
        ax.set_title(f"Readout amplitude optimization")
        ax.set_xlabel("Readout amplitude (V)")
        ax.set_ylabel("SNR")
        return fig
