import math
import re


class _Units:
    """Units for use by QUA programs."""
    ns = 1
    us = 1_000
    ms = 1_000_000
    s = 1_000_000_000

    Hz = 1
    kHz = 1_000
    MHz = 1_000_000
    GHz = 1_000_000_000

    V = 1
    mV = 1e-3
    uV = 1e-6
    nV = 1e-9

    def __setattr__(self, name, value):
        raise AttributeError("Units are read-only")

    def __delattr__(self, name, value):
        raise AttributeError("Units are read-only")

units = _Units()


def extract_unit_prefix(unit):
    """ Take a string describing a unit and extract the multiplier and the unprefixed unit. """
    prefixes = {
        'T': 10**12,
        'G': 10**9,
        'M': 10**6,
        'k': 10**3,
        'd': 10**-1,
        'c': 10**-2,
        'm': 10**-3,
        'u': 10**-6,
        'µ': 10**-6,
        'n': 10**-9,
        'p': 10**-12,
        'f': 10**-15,
    }
    prefix_letters = ''.join(prefixes.keys())
    m = re.match(rf'(2pi)?([{prefix_letters}])?(.*)', unit)
    multiplier = 1
    if m.group(1) == '2pi':
        multiplier *= 2 * math.pi
    unit_base = m.group(3)
    if p := m.group(2):
        if unit_base:
            multiplier *= prefixes[p]
        else:
            unit_base = p  # m is meter, not milli-nothing
    return multiplier, unit_base


def try_to_match_units(unit1, unit2):
    """ Try to match unit1 to unit2: 1 unit1 = return_value unit2. """
    multiplier1, unit_base1 = extract_unit_prefix(unit1)
    multiplier2, unit_base2 = extract_unit_prefix(unit2)
    if unit_base1 == unit_base2:
        return multiplier1 / multiplier2
    else:
        print(f"[!] Units {unit1} and {unit2} could not be matched.")
        return None  # Units could not be matched
