from typing import Dict
import numpy as np
import time

from qxp.instruments.APUASYN20 import APUASYN20
from qxp.instruments.ASPIN20G import ASPIN20G
from qxp.instruments.BN103 import BN103


# TODO: place in config
APUASYN20_VISA_ADDRESS = 'TCPIP0::192.168.0.58::inst0::INSTR'
ASPIN20G_VISA_ADDRESS = 'TCPIP0::192.168.0.43::inst0::INSTR'
BILT100_IP_ADDRESS = '192.168.0.136'

VOLTAGE_SAFETY_VALUE = 10  # 10V --(R=5kOhm)--> 2 mA (consider increasing this value)


def configure_instruments(config: Dict, **kwargs):
    # Get the configuration parameters
    params_list = [config['readout'], config['transmon'], config['memory']]

    # Connect to the instruments
    anapico_lo = APUASYN20(visa_address=APUASYN20_VISA_ADDRESS)
    anapico_twpa = ASPIN20G(visa_address=ASPIN20G_VISA_ADDRESS)
    bn100 = BN103(ip=BILT100_IP_ADDRESS)

    # Set the LO source parameters
    for params in params_list:
        anapico_lo.set_frequency_hz(channel=params['lo_channel'], frequency_hz=params['lo_frequency'])
        anapico_lo.set_power_dbm(channel=params['lo_channel'], power_dbm=params['lo_power'])
        anapico_lo.set_output(channel=params['lo_channel'], output=params['lo_output'])

    # Set the TWPA pump
    anapico_twpa.set_power_dbm(power_dbm=config['twpa']['power'])
    anapico_twpa.set_frequency_hz(frequency_hz=config['twpa']['frequency'])
    anapico_twpa.set_output(output=config['twpa']['output'])

    # Set the coil voltage
    if kwargs.get('ramp_voltage', True):
        voltage_target = config['coil']['voltage']
        if np.abs(voltage_target) >= VOLTAGE_SAFETY_VALUE:

            user_response = bool(input(f'Ramp coil voltage to {voltage_target} V - No (0) or Yes (1)?'))
        else:
            user_response = True

        if user_response:
            step_duration_ns = config['coil']['step_duration']
            ramp_duration_ms = bn100.ramp_voltage(module=config['coil']['module'],
                                                  channel=1,
                                                  value=voltage_target,
                                                  step_duration_ms=step_duration_ns / 1e6,  # convert ns to ms
                                                  step_height_v=config['coil']['step_height'])

            print(f'Ramping the voltage on the coil to {voltage_target} V. '
                  f'Ramp duration is {ramp_duration_ms / 1e3} seconds.')

            time.sleep(ramp_duration_ms / 1e3)
        else:
            print('Ramping coil voltage aborted by user.')

    # Close the instruments
    anapico_lo.close()
    bn100.close()

def turn_off_instruments(config: Dict):
    # Connect to the instruments
    anapico_lo = APUASYN20(visa_address=APUASYN20_VISA_ADDRESS)
    anapico_twpa = ASPIN20G(visa_address=ASPIN20G_VISA_ADDRESS)
    bn100 = BN103(ip=BILT100_IP_ADDRESS)

    # Turn off lo sources
    for channel in [1, 2, 3, 4]:
        anapico_lo.set_output(channel=channel, output=False)

    # Turn off TWPA pump
    anapico_twpa.set_output(output=False)

    # Ramp down the coil voltage and turn off
    module = config['coil']['module']
    bn100.ramp_voltage(module=module, channel=1, value=0, step_duration_ms=100, step_height_v=0.1)
    bn100.set_output(module=module, channel=1, state='off')
