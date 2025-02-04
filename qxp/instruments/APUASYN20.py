import pyvisa
import time
import re
import numpy as np
from typing import Literal, Union


CHANNEL_IDS = Literal[1, 2, 3, 4]
REFERENCE_SOURCES = Literal['INT', 'EXT']
MIN_POWER = -10
MAX_POWER = 23
MIN_FREQUENCY = int(100e3)
MAX_FREQUENCY = int(20e9)


class APUASYN20:
    def __init__(self, visa_address: str):
        self.address = visa_address
        self.instrument = None
        self.connect()
        self.idn = self.query('*IDN?')
        # self.name = re.search(r'\[(.*?)]', self.idn).group(1)
        # self.serial = self.idn.split(",")[2]

    def connect(self) -> None:
        rm = pyvisa.ResourceManager()
        self.instrument = rm.open_resource(self.address)

    def close(self) -> None:
        self.instrument.close()

    def query(self, command: str) -> str:
        return self.instrument.query(command)

    def write(self, command: str) -> None:
        self.instrument.write(command)
        time.sleep(0.2)

    def get_output(self, channel: CHANNEL_IDS) -> bool:
        self._verify_channel(channel)
        response = self.query(command=f':OUTPut{channel}:STATe?')
        return bool(int(response))

    def set_output(self, channel: CHANNEL_IDS, output: bool) -> None:
        self._verify_channel(channel)
        self._verify_output(output)
        if output:
            self.write(f':OUTPut{channel}:STATe ON')
        else:
            self.write(f':OUTPut{channel}:STATe OFF')

    def get_frequency_hz(self, channel: CHANNEL_IDS) -> float:
        self._verify_channel(channel)
        response = self.query(command=f':SOURce{channel}:FREQuency:CW?')
        response = np.round(float(response), 3)
        return response

    def set_frequency_hz(self, channel: CHANNEL_IDS, frequency_hz: Union[int, float]) -> None:
        self._verify_channel(channel)
        self._verify_frequency(frequency_hz)
        self.write(f':SOURce{channel}:FREQuency:CW {frequency_hz}')

    def get_power_dbm(self, channel: CHANNEL_IDS) -> float:
        self._verify_channel(channel)
        response = self.query(f":SOURce{channel}:POWer:LEVel:IMMediate:AMPLitude?")
        response = np.round(float(response), 2)
        return response

    def set_power_dbm(self, channel: CHANNEL_IDS, power_dbm: float) -> None:
        self._verify_channel(channel)
        self._verify_power(power_dbm)
        self.write(command=f':SOURce{channel}:POWer:LEVel:IMMediate:AMPLitude {power_dbm}')

    def get_reference_source(self) -> str:
        response = self.query(f':ROSCillator:SOURce?')
        return response

    def set_reference_source(self, reference_source: REFERENCE_SOURCES) -> None:
        self.write(f'ROSCillator:SOURce {reference_source}')

    def get_reference_frequency_hz(self) -> float:
        response = self.query(f':ROSCillator:EXTernal:FREQuency?')
        return float(response)

    def set_reference_frequency_hz(self, reference_frequency_hz: float) -> None:
        self._verify_reference_frequency(reference_frequency_hz)
        self.write(f':ROSCillator:EXTernal:FREQuency {reference_frequency_hz}')

    def get_reference_output(self) -> bool:
        response = self.query(f':ROSCillator:OUTPut:STATe?')
        return bool(int(response))

    def set_reference_output(self, reference_output: bool) -> None:
        self._verify_output(reference_output)
        if reference_output:
            self.write(f':ROSCillator:OUTPut:STATe ON')
        else:
            self.write(f':ROSCillator:OUTPut:STATe OFF')

    def get_lock_state(self) -> bool:
        response = self.query(f':ROSCillator:LOCKed?')
        return bool(int(response))

    @staticmethod
    def _verify_output(output) -> None:
        if not isinstance(output, bool):
            raise TypeError('Invalid output state. Must be a True or False.')

    @staticmethod
    def _verify_channel(channel) -> None:
        if channel not in [1, 2, 3, 4]:
            raise Exception('Invalid channel ID. Must be 1, 2, 3 or 4.')

    @staticmethod
    def _verify_power(power_dbm) -> None:
        if not isinstance(power_dbm, (int, float)):
            raise TypeError('Invalid power_dbm type. Must be integer or float.')
        if power_dbm < MIN_POWER or power_dbm > MAX_POWER:
            raise ValueError(f'Invalid power_dbm value. Must be between {MIN_POWER} and {MAX_POWER}.')

    @staticmethod
    def _verify_frequency(frequency_hz) -> None:
        if not isinstance(frequency_hz, (int, float)):
            raise TypeError('Invalid frequency_hz type. Must be integer or float.')
        if frequency_hz < MIN_FREQUENCY or frequency_hz > MAX_FREQUENCY:
            raise ValueError(f'Invalid frequency_hz value. Must be between {MIN_FREQUENCY} and {MAX_FREQUENCY}.')

    @staticmethod
    def _verify_reference_type(reference_source) -> None:
        if not isinstance(reference_source, str):
            raise TypeError('Invalid reference type. Must be a string.')
        if not reference_source == 'INT' or reference_source == 'EXT':
            raise ValueError('Invalid reference type. Must be INT or EXT.')

    @staticmethod
    def _verify_reference_frequency(reference_frequency_hz) -> None:
        if int(reference_frequency_hz) != int(10e6) and int(reference_frequency_hz) != int(100e6):
            raise ValueError('Invalid reference frequency. Must be 10 MHz or 100 MHz.')
