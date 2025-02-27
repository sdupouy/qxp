from pathlib import Path
from qualang_tools.units import unit
import numpy as np
u = unit()

from qxp.utils.qua import iq_imbalance_k_theta
from qxp.utils.waveforms import gaussian_shape


BASE_SAVE_PATH = Path(r'D:\data\tunable_autocat_qxp')
CHIP_NAME = 'RC-0008-01-C-bottom'
COOLDOWN_NUMBER = 1
RACK_NAME = 'Australie'

# The experiment configuration is used to build the QUA configuration dictionary.
EXP_CONFIG = {
    "ro_resonator": {
        "lo": "ro_resonator_lo",
        "i_freq": 60 * u.MHz,
        "sideband": -1,

        "resonance_freq": 6.93874 * u.GHz,
        "pulse_length": int(10000 * u.ns),
        "pulse_amp": 0.3,

        "time_of_flight": 360 * u.ns,
        "readout_phase": 0 * 2*np.pi,
        "reset_time": 5000 * u.ns
    },

    "transmon": {
        "lo": "transmon_lo",
        "i_freq": 90 * u.MHz,
        "sideband": -1,

        "resonance_freq": 2.6922 * u.GHz,
        "pi_pulse_length": int(1000 * u.ns),
        "pi_pulse_amp": 0.005,
        "saturation_pulse_length": int(1000 * u.ns),
        "saturation_pulse_amp": 0.005,

        "reset_time": 100_000 * u.ns,
    },

    "memory": {
        "lo": "memory_lo",
        "i_freq": 100 * u.MHz,
        "sideband": -1,

        "pulse_length": int(100 * u.ns),
        "const_pulse_amp": 0.02,
        "gaussian_pulse_amp": 0.2,

        "i_offset": -0.01721,
        "q_offset": -0.00985,
        "k": 1.015,
        "theta": 1.6,
    },

    "coil": {
        "dc_source": "coil_dc_source"
    },

    "twpa": {
        "pump": "twpa_pump"
    }
}
# These parameters provide default values that can be overridden by database values.

INSTRUMENTS_CONFIG = {
    "ro_resonator_lo": {
        "class": "APUASYN20",
        "address": "TCPIP0::192.168.0.58::inst0::INSTR",
        "channel": 1,
        "output": True,
        "frequency": 7.0 * u.GHz,
        "power": 18  # dBm
    },
    "transmon_lo": {
        "class": "APUASYN20",
        "address": "TCPIP0::192.168.0.58::inst0::INSTR",
        "channel": 2,
        "output": False,
        "frequency": 7.0 * u.GHz,
        "power": 18  # dBm
    },
    "memory_lo": {
        "class": "APUASYN20",
        "address": "TCPIP0::192.168.0.58::inst0::INSTR",
        "channel": 3,
        "output": False,
        "frequency": 7.0 * u.GHz,
        "power": 18  # dBm
    },
    "twpa_pump": {
        "class": "ASPIN20G",
        "address": "TCPIP0::192.168.0.43::inst0::INSTR",
        "output": False,
        "frequency": 7.0 * u.GHz,
        "power": 18  # dBm
    },
    "coil_dc_source": {
        "class": "BN103",
        "address": "192.168.0.136",
        "module": 1,
        "channel": 1,
        "voltage": 0.0 * u.V,
        "resistor": 5 * 1e3,  # Ohm
        "step_duration": 200 * u.ms,
        "step_height": 100 * u.mV
    }
}

def get_qua_config(exp_config, instruments_config):
    memory_lo = instruments_config[exp_config["memory"]["lo"]]
    config = {
        'version': 1,

        'controllers': {
            'con1': {
                'type': 'opx1',
                'analog_outputs': {
                    1: {'offset': 0},  # readout resonator
                    2: {'offset': 0},  # transmon
                    3: {'offset': exp_config['memory']['i_offset']},  # memory I
                    4: {'offset': exp_config['memory']['q_offset']},  # memory Q
                    10: {'offset': 0.0}  # SQUID DC
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

            'memory': {
                'mixInputs': {
                    'I': ('con1', 3),
                    'Q': ('con1', 4),
                    'lo_frequency': memory_lo['frequency'],
                    'mixer': 'memory_mixer',
                },
                'intermediate_frequency': exp_config['memory']['i_freq'],
                'operations': {
                    'memory_const': 'memory_const',
                    'displacement': 'displacement',
                }
            },

            'squid_flux': {
                'singleInput': {'port': ('con1', 10)},
                'intermediate_frequency': 0,
                'operations': {
                    'const': 'const_flux_pulse'
                }
            }
        },

        'mixers': {
            'memory_mixer': [
                {
                    'intermediate_frequency': exp_config['memory']['i_freq'],
                    'lo_frequency': memory_lo['frequency'],
                    'correction': iq_imbalance_k_theta(exp_config['memory']['k'], exp_config['memory']['theta']),
                }
            ],
        },

        'pulses': {
            'readout': {
                'operation': 'measurement',
                'length': exp_config['ro_resonator']['pulse_length'],
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

            'transmon_saturation': {
                'operation': 'control',
                'length': exp_config['transmon']['saturation_pulse_length'],
                'waveforms': {
                    'single': 'transmon_saturation_wave',
                }
            },

            'memory_const': {
                'operation': 'control',
                'length': exp_config['memory']['pulse_length'],
                'waveforms': {
                    'I': 'memory_const_wave',
                    'Q': 'zero_wave',
                },
            },

            'displacement': {
                'operation': 'control',
                'length': exp_config['memory']['pulse_length'],
                'waveforms': {
                    'I': 'memory_wave',
                    'Q': 'zero_wave',
                },
            },

            'const_flux_pulse': {
                'operation': 'control',
                'length': 1000,
                'waveforms': {
                    'single': 'const_flux_wave',
                }
            }
        },

        'waveforms': {
            'readout_wave': {
                'type': 'constant',
                'sample': exp_config['ro_resonator']['pulse_amp'],
            },

            'zero_wave': {
                'type': 'constant',
                'sample': 0
            },

            'transmon_pi_wave': {
                'type': 'arbitrary',
                'samples': gaussian_shape(exp_config['transmon']['pi_pulse_amp'],
                                          exp_config['transmon']['pi_pulse_length'],
                                          exp_config['transmon']['pi_pulse_length'] / 6,
                                          padding=True)
            },

            'memory_wave': {
                'type': 'arbitrary',
                'samples': gaussian_shape(exp_config['memory']['gaussian_pulse_amp'],
                                          exp_config['memory']['pulse_length'],
                                          exp_config['memory']['pulse_length'] / 6,
                                          padding=True)
            },

            'memory_const_wave': {
                'type': 'constant',
                'sample': exp_config['memory']['const_pulse_amp'],
            },

            'transmon_saturation_wave': {
                'type': 'constant',
                'sample': exp_config['transmon']['saturation_pulse_amp'],
            },

            'const_flux_wave': {
                'type': 'constant',
                'sample': 0.0
            },
        },

        'digital_waveforms': {
            'ON': {
                'samples': [(1, 0)]
            }
        },

        'integration_weights': {
            'cosine_weights': {
                'cosine': [(1.0, exp_config['ro_resonator']['pulse_length'])],
                'sine': [(0.0, exp_config['ro_resonator']['pulse_length'])],
            },
            'sine_weights': {
                'cosine': [(0.0, exp_config['ro_resonator']['pulse_length'])],
                'sine': [(1.0, exp_config['ro_resonator']['pulse_length'])],
            },
            'minus_sine_weights': {
                'cosine': [(0.0, exp_config['ro_resonator']['pulse_length'])],
                'sine': [(-1.0, exp_config['ro_resonator']['pulse_length'])],
            },
        }
    }

    return config
