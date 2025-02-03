import numpy as np
import time


def iq_imbalance(g, phi):
    """
    Creates the correction matrix for the mixer imbalance caused by the gain and phase imbalances, more information can
    be seen here: https://docs.qualang.io/libs/examples/mixer-calibration/#non-ideal-mixer

    Args:
        g: relative gain imbalance between the 'I' & 'Q' ports. (unit-less), set to 0 for no gain imbalance.
        phi: relative phase imbalance between the 'I' & 'Q' ports (radians), set to 0 for no phase imbalance.
    """
    c = np.cos(phi)
    s = np.sin(phi)
    n = 1 / ((1 - g ** 2) * (2 * c ** 2 - 1))
    return [float(n * x) for x in [(1 - g) * c, (1 + g) * s, (1 - g) * s, (1 + g) * c]]


def iq_imbalance_k_theta(k, theta):
    r = [[np.cos(theta), np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    c = [[k, 0], [0, 1 / k]]
    return tuple(np.around(np.matmul(c, r), 6).flatten())


def ns2cycle(t):
    """ Convert time in ns to a number of FPGA cycles (4 ns). """
    return t // 4


def wait_until_job_is_paused(current_job):
    """
    Waits until the OPX FPGA reaches the pause statement.
    Used when the OPX sequence needs to be synchronized with an external parameter sweep.

    Args:
        current_job: the job object.
    """
    while not current_job.is_paused():
        time.sleep(0.1)
        pass
    return True
