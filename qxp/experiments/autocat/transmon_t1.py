import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from qm.qua import *
from qualang_tools.units import unit
from qualang_tools.loops import from_array
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.experiments.autocat.config import autoconfig
from qxp.utils.fit import exponential_fit


class TransmonT1(BaseQuaExperiment):
    """
    TRANSMON T1 MEASUREMENT
    The sequence consists in putting the transmon in the excited stated by playing the pi pulse and measuring the resonator
    after a varying time. The transmon T1 is extracted by fitting the exponential decay of the measured quadratures.

    Prerequisites:
        - Having measured the readout resonator frequency.
        - Having calibrated the transmon pi pulse.
    """
    identifier = 'transmon_t1'
    display_name = 'Transmon T1'

    def __init__(self, taus=None, n_avg=1000, **kwargs):
        """
        Args:
            taus: The waiting times, in nanoseconds (values should be multiples of 4).
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.taus = np.arange(16 // 4, 40_000 // 4, 100 // 4) if taus is None else taus // 4
        self.n_avg = n_avg

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)

    def get_qua_program(self):
        """ QUA program """
        time_steps = len(self.taus)
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']

        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            t = declare(int)  # QUA variable for the wait time
            I = declare(fixed)  # QUA variable for the measured 'I' quadrature
            Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
            I_st = declare_stream()  # Stream for the 'I' quadrature
            Q_st = declare_stream()  # Stream for the 'Q' quadrature
            n_st = declare_stream()  # Stream for the averaging iteration 'n'

            with for_(n, 0, n < self.n_avg, n + 1):
                with for_(*from_array(t, self.taus)):
                    # Play the x180 gate to put the transmon in the excited state
                    play("transmon_pi", "transmon")
                    # Wait a varying time after putting the transmon in the excited state
                    wait(t, "transmon")
                    # Align the two elements to measure after having waited a time "tau" after the transmon pulse.
                    align("transmon", "ro_resonator")
                    # Measure the state of the resonator
                    measure(
                        "readout",
                        "ro_resonator",
                        None,
                        demod.full("sin", I),
                        demod.full("cos", Q),
                    )
                    # Wait for the transmon to decay to the ground state
                    wait(u.to_clock_cycles(ro_reset_time), "ro_resonator")
                    # Save the 'I_e' & 'Q_e' quadratures to their respective streams
                    save(I, I_st)
                    save(Q, Q_st)
                # Save the averaging iteration to get the progress bar
                save(n, n_st)

            with stream_processing():
                I_st.buffer(time_steps).average().save("I")
                Q_st.buffer(time_steps).average().save("Q")
                n_st.save("iteration")

        return prog

    def get_data(self, result_handles):
        i_rawdata = result_handles.get("I").fetch_all()
        q_rawdata = result_handles.get("Q").fetch_all()
        iteration = result_handles.get("iteration").fetch_all()

        readout_pulse_length = self.exp_config['readout']['ro_pulse_length']
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def fit(self):
        p0 = [0.0005, 20_000, 0]
        popt, pcov = curve_fit(exponential_fit, self.taus * 4, np.abs(self.data['iq_data']), p0=p0)
        t1 = popt[1]

        self.fit_params = {
            'popt': popt,
        }

        print(f"Transmon T1 is {t1 / u.us:.01f} µs")

        return {
            'transmon_t1': t1,
        }

    def plot(self):
        fig, ax = plt.subplots()
        ax.plot(self.taus * 4, np.abs(self.data['iq_data']))
        if self.fit_params:
            ax.plot(self.taus * 4, exponential_fit(self.taus * 4, self.fit_params['popt']))
        return fig
