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


def wait_until_job_is_paused(job):
    """
    Waits until the OPX FPGA reaches the pause statement.
    Used when the OPX sequence needs to be synchronized with an external parameter sweep.

    Args:
        job: the job object.
    """
    while not job.is_paused():
        time.sleep(0.1)
        pass
    return True


def result_handles_to_data_dict(result_handles):
    """ Build a data dictionary from a StreamingResultFetcher (result_handles) object. """
    def unpack_values(data):
        """ Unpack structured NumPy dtype if needed. """
        if data.dtype.names is not None:
            data = data["value"]
        return data

    data_dict = {}
    for name, handle in result_handles:
        data_dict[name] = unpack_values(handle.fetch_all())
    return data_dict


def truncate_to_smallest(arrays):
    """ Truncate all arrays to the length of the smallest. """
    min_length = min([len(a) for a in arrays])
    return [a[:min_length] for a in arrays]


def format_progress(progress):
    """ Format a percentage into a progress bar. """
    bar = '=' * (round(progress) // 2) + ' ' * (50 - (round(progress) // 2))
    return f"Progress [{bar}] {progress:.1f}%"

def demod2volts(data, duration, single_demod=False):
    """ Converts the demodulated data to volts.
    Args:
        data (float or ndarray): demodulated data.
        duration (int): demodulation duration in ns. This must be the duration of one slice in the case of `demod.sliced` and `demod.accumulated`.
        single_demod (bool): Flag to add the additional factor of 2 needed for single demod.
    Returns:
        The demodulated data in volts.
    """
    if single_demod:
        return 2 * 4096 * data / duration
    else:
        return 4096 * data / duration


def raw2volts(data):
    """ Converts the raw data to volts.
    Args:
        data (float or ndarray): raw data.
    Returns:
        The raw data in volts.
    """
    return data / 4096
