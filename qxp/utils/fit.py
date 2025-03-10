import numpy as np


""" Fitting functions """

def fit_cosine(t, amplitude, period, phase, offset):
    return amplitude * np.cos(2 * np.pi * t / period + phase) + offset


def fit_decaying_cosine(t, amplitude, period, tau, phase, offset):
    return amplitude * np.cos(2 * np.pi * t / period + phase) * np.exp(-t/ tau) + offset

def exponential_fit(t, a, tau, offset):
    return a * np.exp(-t / tau) + offset


""" Fitting utils """

def cosine_tmax_from_popt(popt):
    amplitude, period, phase, offset = popt
    if amplitude < 0:
        phase += np.pi
    phase %= 2*np.pi
    return period - phase * period / (2 * np.pi)
