import numpy as np
from dataclasses import field


def copy_default(v):
    """
    Builds a deep copied default for mutable experiment parameters.

    Usage:
        delays: np.ndarray = copy_default([0, 20e-9, 40e-9])
    """
    if isinstance(v, np.ndarray):
        return field(default_factory=lambda: arr.copy())
    if isinstance(v, (dict, list, tuple, set)):
        return field(default_factory=lambda: copy.deepcopy(d))
    return field(default=v)
