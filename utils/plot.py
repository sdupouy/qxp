from typing import Union, List
from matplotlib.pyplot import Axes
import numpy as np


def apply_to_axes(axes: Union[Axes, List, np.ndarray], func):
    if isinstance(axes, Axes):
        func(axes)
    elif isinstance(axes, List) or isinstance(axes, np.ndarray):
        for ax in axes:
            apply_to_axes(ax, func)
    else:
        raise TypeError('Invalid type for axes.')

def clean_axes(axes: Union[Axes, List, np.ndarray]):
    def clean(ax: Axes):
        for line in ax.lines:
            line.remove()

    apply_to_axes(axes, clean)

def clean_axes_2d(axes: Union[Axes, List, np.ndarray]):
    def clean(ax: Axes):
        for quad in ax.collections:
            quad.remove()

    apply_to_axes(axes, clean)

def adjust_axes_limits(axes: Union[Axes, List, np.ndarray]):
    def adjust(ax: Axes):
        ax.relim()
        ax.autoscale_view()

    apply_to_axes(axes, adjust)
