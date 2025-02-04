from pathlib import Path
from qualang_tools.units import unit
import numpy as np
u = unit()

from qxp.utils.qua import iq_imbalance_k_theta
from qxp.utils.waveforms import gaussian_shape


BASE_SAVE_PATH = Path(r'D:\data\tunable_autocat')
CHIP_NAME = 'RC-0008-01-B-top'
COOLDOWN_NUMBER = 5

CONFIG_PARAMS = {
    "elements": {
        "readout": {
            "lo": "ro_resonator_lo",
            "pulse_length": 3000 * u.ns,
            "pulse_amp": 0.05,

            "im_frequency": 61 * u.MHz,
            "sideband": -1,

            "time_of_flight": 360 * u.ns,
            "readout_phase": 0 * 2*np.pi,

            "reset_time": 5000 * u.ns
        },

        "transmon": {
            "pulse_length": 1000 * u.ns,
            "pulse_amp": 0.005,

            "lo_channel": 2,
            "lo_output": True,
            "lo_power": 15,  # dBm
            "lo_frequency": 2.7822 * u.GHz,
            "im_frequency": 90 * u.MHz,
            "sideband": -1,

            "resonance_frequency": 2.6922 * u.GHz
        },

        "memory": {
            "pulse_length": 100 * u.ns,
            "const_pulse_amp": 0.02,
            "gaussian_pulse_amp": 0.2,

            "lo_channel": 3,
            "lo_output": True,
            "lo_power": 15,  # dBm
            "lo_frequency": 3.55 * u.GHz,
            "im_frequency": 100 * u.MHz,
            "sideband": -1,

            "i_offset": -0.01721,
            "q_offset": -0.00985,
            "k": 1.015,
            "theta": 1.6,

            "resonance_frequency": 3.45818 * u.GHz
        },

        "coil": {
            "dc_source": "coil_dc_source"
        },

        "twpa": {
            "pump": "twpa_pump"
        }
    },
    "instruments": {
        "ro_resonator_lo": {
            "class": "APUASYN20",
            "address": "TCPIP0::192.168.0.58::inst0::INSTR",
            "channel": 1,
            "output": False,
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
}

def get_qua_config(params):
    config = {
        'version': 1,

        'controllers': {
            'con1': {
                'type': 'opx1',
                'analog_outputs': {
                    1: {'offset': 0},  # readout resonator
                    2: {'offset': 0},  # transmon
                    3: {'offset': params['memory']['i_offset']},  # memory I
                    4: {'offset': params['memory']['q_offset']},  # memory Q
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
            'readout_resonator': {
                'singleInput': {
                    'port': ('con1', 1),
                },
                'intermediate_frequency': params['readout']['im_frequency'],
                'operations': {
                    'readout': 'readout',
                },
                'outputs': {
                    'out1': ('con1', 1)
                },
                'time_of_flight': params['readout']['time_of_flight'],
                'smearing': 0,
            },

            'transmon': {
                "singleInput": {
                    'port': ('con1', 2),
                },
                'intermediate_frequency': params['transmon']['im_frequency'],
                'operations': {
                    'transmon_pulse': 'transmon_pulse',
                    'transmon_const': 'transmon_const',
                }
            },

            'memory': {
                "mixInputs": {
                    "I": ('con1', 3),
                    "Q": ('con1', 4),
                    "lo_frequency": params['memory']['lo_frequency'],
                    "mixer": "memory_mixer",
                },
                'intermediate_frequency': params['memory']['im_frequency'],
                'operations': {
                    'memory_const': 'memory_const',
                    'displacement': 'displacement',
                }
            },

            'squid_flux': {
                'singleInput': {'port': ('con1', 10)},
                'intermediate_frequency': int(0e6),
                'operations': {"const": "const_flux_pulse"}
            }
        },

        'mixers': {
            "memory_mixer": [
                {
                    "intermediate_frequency": params['memory']['im_frequency'],
                    "lo_frequency": params['memory']['lo_frequency'],
                    "correction": iq_imbalance_k_theta(params['memory']['k'], params['memory']['theta']),
                }
            ],
        },

        'pulses': {
            'readout': {
                'operation': 'measurement',
                'length': params['readout']['pulse_length'],
                'waveforms': {
                    'single': 'readout_wave'
                },
                'integration_weights': {
                    "cos": "cosine_weights",
                    "sin": "sine_weights",
                    "minus_sin": "minus_sine_weights",
                },
                "digital_marker": "ON",
            },

            'transmon_pulse': {
                'operation': 'control',
                'length': params['transmon']['pulse_length'],
                'waveforms': {
                    'single': 'transmon_wave',
                }
            },

            'transmon_const': {
                'operation': 'control',
                'length': params['transmon']['pulse_length'],
                'waveforms': {
                    'single': 'transmon_const_wave',
                }
            },

            "memory_const": {
                "operation": "control",
                "length": params['memory']['pulse_length'],
                "waveforms": {
                    "I": "memory_const_wave",
                    "Q": "zero_wave",
                },
            },

            "displacement": {
                "operation": "control",
                "length": params['memory']['pulse_length'],
                "waveforms": {
                    "I": "memory_wave",
                    "Q": "zero_wave",
                },
            },

            "const_flux_pulse": {
                "operation": "control",
                "length": 1000,
                "waveforms": {
                    "single": "const_flux_wave",
                }
            }
        },

        'waveforms': {
            'readout_wave': {
                'type': 'constant',
                'sample': params['readout']['pulse_amp'],
            },

            'zero_wave': {
                'type': 'constant',
                'sample': 0
            },

            'transmon_wave': {
                'type': 'arbitrary',
                'samples': gaussian_shape(params['transmon']['pulse_amp'],
                                          params['transmon']['pulse_length'],
                                          params['transmon']['pulse_length'] / 6,
                                          padding=True)
            },

            'memory_wave': {
                'type': 'arbitrary',
                'samples': gaussian_shape(params['memory']['gaussian_pulse_amp'],
                                          params['memory']['pulse_length'],
                                          params['memory']['pulse_length'] / 6,
                                          padding=True)
            },

            'memory_const_wave': {
                'type': 'constant',
                'sample': params['memory']['const_pulse_amp'],
            },

            'transmon_const_wave': {
                'type': 'constant',
                'sample': params['transmon']['pulse_amp'],
            },


            "const_flux_wave": {"type": "constant",
                                "sample": 0.0},
        },

        'digital_waveforms': {
            'ON': {
                'samples': [(1, 0)]
            }
        },

        'integration_weights': {
            "cosine_weights": {
                "cosine": [(1.0, params['readout']['pulse_length'])],
                "sine": [(0.0, params['readout']['pulse_length'])],
            },
            "sine_weights": {
                "cosine": [(0.0, params['readout']['pulse_length'])],
                "sine": [(1.0, params['readout']['pulse_length'])],
            },
            "minus_sine_weights": {
                "cosine": [(0.0, params['readout']['pulse_length'])],
                "sine": [(-1.0, params['readout']['pulse_length'])],
            },
        }
    }

    return config
