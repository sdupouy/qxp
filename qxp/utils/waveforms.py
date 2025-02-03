import numpy as np


def gaussian_shape(amp, total_time, sigma, padding=True):
    """ Return an array of gaussian shape. """
    pad_time = 0
    if padding:
        if total_time < 16:
            pad_time = 16 - total_time
        else:
            pad_time = - total_time % 4
    time = np.arange(total_time)
    gaussian = np.exp(-np.square(time - total_time / 2) / (2 * sigma ** 2))
    return list(amp * gaussian) + [0.0] * pad_time
