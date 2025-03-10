import matplotlib.pyplot as plt
import numpy as np

from qm.qua import *
from qualang_tools.units import unit
u = unit()

from qxp.experiments.base_experiment import BaseQuaExperiment
from qxp.experiments.autocat.config import autoconfig
from qxp.utils.instruments import get_instrument_by_name
from qxp.utils.qua import wait_until_job_is_paused


class TWPAOptimization(BaseQuaExperiment):
    """
    TWPA OPTIMIZATION
    The code runs a loop on the TWPA pump power and frequency to optimize the SNR of the readout.

    Prerequisites:
        - Having measured the readout resonator frequency.
        - Having calibrated the transmon pi pulse.
    """
    identifier = 'twpa_optimization'
    display_name = 'TWPA pump optimization'

    def __init__(self, powers, freqs, n_avg=1000, **kwargs):
        """
        Args:
            powers: The array of powers to sweep, in dBm.
            freqs: The array of frequencies to sweep, in Hertz.
            n_avg: The averaging.
        """
        super().__init__(**kwargs)
        self.powers = powers
        self.freqs = freqs
        self.n_avg = n_avg

    def auto_set_exp_config(self):
        """ Automatically set the parameters of the experiment. """
        autoconfig.auto_set_exp_config(self.exp_config)

    def auto_set_instruments_config(self):
        """ Automatically set the instruments' initialization parameters. """
        autoconfig.auto_set_instruments_config(self.instruments_config, self.exp_config)

    def get_qua_program(self):
        ro_reset_time = self.exp_config['ro_resonator']['reset_time']
        transmon_reset_time = self.exp_config['transmon']['reset_time']

        """ QUA program """
        with program() as prog:
            n = declare(int)  # QUA variable for the averaging loop
            i = declare(int)  # QUA variable for the power and frequency sweeps

            I0 = declare(fixed)
            Q0 = declare(fixed)
            I = declare(fixed)
            Q = declare(fixed)

            I0_st = declare_stream()
            Q0_st = declare_stream()
            I_st = declare_stream()
            Q_st = declare_stream()

            with for_(i, 0, i < len(self.powers) * len(self.freqs), i + 1):
                pause()  # wait until LO frequency is updated
                with for_(n, 0, n < self.n_avg, n + 1):
                    align()
                    measure(
                        "readout",
                        "ro_resonator",
                        None,
                        demod.full("sin", I0),
                        demod.full("cos", Q0),
                    )
                    wait(u.to_clock_cycles(ro_reset_time), "ro_resonator")

                    align()
                    play("transmon_pulse", "transmon")
                    align("transmon", "ro_resonator")
                    measure(
                        "readout",
                        "ro_resonator",
                        None,
                        demod.full("sin", I),
                        demod.full("cos", Q),
                    )
                    wait(u.to_clock_cycles(transmon_reset_time), "ro_resonator")  # Wait for the transmon to decay to the ground state

                    save(I0, I0_st)
                    save(Q0, Q0_st)
                    save(I, I_st)
                    save(Q, Q_st)
            pause()

            with stream_processing():
                I0_st.buffer(self.n_avg).save_all("I0")
                Q0_st.buffer(self.n_avg).save_all("Q0")
                I_st.buffer(self.n_avg).save_all("I")
                Q_st.buffer(self.n_avg).save_all("Q")

        return prog

    def manage_job_pauses(self, job):
        twpa_pump = get_instrument_by_name(self.exp_config['twpa']['pump'], self.instruments_config)

        for power in self.powers:
            twpa_pump.set_power_dbm(power_dbm=power)
            for freq in self.freqs:
                twpa_pump.set_frequency_hz(frequency_hz=freq)
                # Resume the QUA program (escape the 'pause' statement)
                job.resume()
                wait_until_job_is_paused(job)
        job.halt()  # otherwise is remains is paused state

    def get_data(self, result_handles):
        i0_rawdata = result_handles.get("I0").fetch_all()
        q0_rawdata = result_handles.get("Q0").fetch_all()
        i_rawdata = result_handles.get("I").fetch_all()
        q_rawdata = result_handles.get("Q").fetch_all()
        iteration = result_handles.get("iteration").fetch_all()

        readout_pulse_length = self.exp_config['readout']['ro_pulse_length']
        iq0_data = u.demod2volts(i0_rawdata + 1j * q0_rawdata, readout_pulse_length, single_demod=True)
        iq_data = u.demod2volts(i_rawdata + 1j * q_rawdata, readout_pulse_length, single_demod=True)
        data = {
            'iq0_data': iq0_data,
            'iq_data': iq_data,
            'iteration': iteration,
        }
        return data

    def fit(self):
        # TODO

        return {
            # KEY: VALUE,
        }

    def plot(self):
        fig, axs = plt.subplots()
        ...  # TODO
        return fig
