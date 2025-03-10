"""
This is an example startup config created upon project creation.
Replace it with your own!
"""

from pathlib import Path
from qualang_tools.units import unit
u = unit()

from qxp.utils.waveforms import gaussian_shape


# Path to the matplotlib custom style to use
MPLSTYLE_PATH = Path(__file__).resolve().parent / 'custom.mplstyle'

# The experiment configuration is used to build the QUA configuration dictionary.
EXP_CONFIG = {
    "ro_resonator": {
        "lo": "ro_resonator_lo",
        "i_freq": 60 * u.MHz,
        "sideband": -1,

        "resonance_freq": 6.0 * u.GHz,
        "ro_pulse_freq": 6.0 * u.GHz,
        "ro_pulse_length": int(10000 * u.ns),
        "ro_pulse_amp": 0.2,

        "time_of_flight": 300 * u.ns,
        "reset_time": 5_000 * u.ns
    },

    "transmon": {
        "lo": "transmon_lo",
        "i_freq": 90 * u.MHz,
        "sideband": -1,

        "resonance_freq": 2.6922 * u.GHz,
        "pi_pulse_length": int(1000 * u.ns),
        "pi_pulse_amp": 0.2,

        "reset_time": 100_000 * u.ns,
    },
}

# The OPX connection parameters
OPX_CONNECTION = {
    'host': '*.*.*.*',
    'port': 9510,
    'cluster_name': 'Cluster_1',
}

# These parameters provide default values that can be overridden by database values.
INSTRUMENTS_CONFIG = {
    "ro_resonator_lo": {
        "class": "APUASYN20",
        "address": "TCPIP0::*.*.*.*::inst0::INSTR",
        "channel": 1,
        "output": True,
        "frequency": 7.0 * u.GHz,
        "power": 18  # dBm
    },
    "transmon_lo": {
        "class": "APUASYN20",
        "address": "TCPIP0::*.*.*.*::inst0::INSTR",
        "channel": 2,
        "output": False,
        "frequency": 7.0 * u.GHz,
        "power": 18  # dBm
    },
}

# This function should return the QUA configuration dictionary
def get_qua_config(exp_config, instruments_config):
    config = {
        'version': 1,

        'controllers': {
            'con1': {
                'type': 'opx1',
                'analog_outputs': {
                    1: {'offset': 0},  # readout resonator
                    2: {'offset': 0},  # transmon
                },
                'digital_outputs': {
                    1: {},
                    2: {}
                },
                'analog_inputs': {
                    1: {'offset': 0.0, 'gain_db': 0},
                }
            }
        },

        'elements': {
            'ro_resonator': {
                'singleInput': {
                    'port': ('con1', 1),
                },
                'intermediate_frequency': exp_config['ro_resonator']['i_freq'],
                'operations': {
                    'readout': 'readout',
                },
                'outputs': {
                    'out1': ('con1', 1)
                },
                'time_of_flight': exp_config['ro_resonator']['time_of_flight'],
                'smearing': 0,
            },

            'transmon': {
                'singleInput': {
                    'port': ('con1', 2),
                },
                'intermediate_frequency': exp_config['transmon']['i_freq'],
                'operations': {
                    'transmon_pi': 'transmon_pi',
                    'transmon_saturation': 'transmon_saturation',
                }
            },
        },

        'mixers': {},

        'pulses': {
            'readout': {
                'operation': 'measurement',
                'length': exp_config['ro_resonator']['ro_pulse_length'],
                'waveforms': {
                    'single': 'readout_wave'
                },
                'integration_weights': {
                    'cos': 'cosine_weights',
                    'sin': 'sine_weights',
                    'minus_sin': 'minus_sine_weights',
                },
                'digital_marker': 'ON',
            },

            'transmon_pi': {
                'operation': 'control',
                'length': exp_config['transmon']['pi_pulse_length'],
                'waveforms': {
                    'single': 'transmon_pi_wave',
                }
            },
        },

        'waveforms': {
            'readout_wave': {
                'type': 'constant',
                'sample': exp_config['ro_resonator']['ro_pulse_amp'],
            },

            'transmon_pi_wave': {
                'type': 'arbitrary',
                'samples': gaussian_shape(exp_config['transmon']['pi_pulse_amp'],
                                          exp_config['transmon']['pi_pulse_length'],
                                          exp_config['transmon']['pi_pulse_length'] / 6,
                                          padding=True)
            },
        },

        'digital_waveforms': {
            'ON': {
                'samples': [(1, 0)]
            }
        },

        'integration_weights': {
            'cosine_weights': {
                'cosine': [(1.0, exp_config['ro_resonator']['ro_pulse_length'])],
                'sine': [(0.0, exp_config['ro_resonator']['ro_pulse_length'])],
            },
            'sine_weights': {
                'cosine': [(0.0, exp_config['ro_resonator']['ro_pulse_length'])],
                'sine': [(1.0, exp_config['ro_resonator']['ro_pulse_length'])],
            },
            'minus_sine_weights': {
                'cosine': [(0.0, exp_config['ro_resonator']['ro_pulse_length'])],
                'sine': [(-1.0, exp_config['ro_resonator']['ro_pulse_length'])],
            },
        }
    }
    return config
