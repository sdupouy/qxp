import numpy as np
from scipy.optimize import minimize


""" Fitting functions """

def fit_cosine(t, amplitude, period, phase, offset):
    return amplitude * np.cos(2 * np.pi * t / period + phase) + offset


def fit_decaying_cosine(t, amplitude, period, tau, phase, offset):
    return amplitude * np.cos(2 * np.pi * t / period + phase) * np.exp(-t/ tau) + offset

def exponential_fit(t, a, tau, offset):
    return a * np.exp(-t / tau) + offset


""" Cost functions """

def threshold_false_positives(threshold, g, e):
    """ Compute the false positive measurements due to a given thresholding """
    assert np.mean(g) < np.mean(e)
    return np.sum(g > threshold) + np.sum(e < threshold)


""" Fitting utils """

def cosine_tmax_from_popt(popt):
    """ Compute the tau of the first maximum of a fitted cosine.
    Args:
        popt (list): The optimal parameters obtained from fitting fit_cosine.
    Returns:
        The time of the first maximum.
    """
    amplitude, period, phase, offset = popt
    if period < 0:
        phase *= -1
        period *= -1
    if amplitude < 0:
        phase += np.pi
    phase %= 2*np.pi
    return period - phase * period / (2 * np.pi)

def threshold_g_e_blobs(g, e):
    """
    Project |g> and |e> IQ blobs on a single axis, and find a threshold maximizing fidelity.
    Args:
        g (ndarray): An array of complex points corresponding to the ground state blob.
        e (ndarray): An array of complex points corresponding to the 1st excited state blob.

    Returns:
        A tuple (g_proj, e_proj, angle, threshold, fidelity), where g_proj and e_proj are the projected points.
    """
    angle = np.angle(np.mean(e) - np.mean(g))
    g_proj = np.real(np.exp(-1j * angle) * g)
    e_proj = np.real(np.exp(-1j * angle) * e)

    threshold_initial = np.mean((g_proj + e_proj) / 2)
    res = minimize(threshold_false_positives, threshold_initial, (g_proj, e_proj), method='Nelder-Mead')
    threshold = res.x[0]

    g_knowing_g = np.sum(g_proj < threshold) / len(g_proj)
    e_knowing_e = np.sum(e_proj > threshold) / len(e_proj)
    fidelity = 100 * (g_knowing_g + e_knowing_e) / 2
    return g_proj, e_proj, angle, threshold, fidelity
