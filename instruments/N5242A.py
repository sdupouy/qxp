"""
Mini driver for the Keysight VNA N5242A.
Assumes single measurement, trace, etc.

"""

import pyvisa
import time
import numpy as np

import matplotlib.pyplot as plt
from typing import Literal

from utilities.plot_utilities import FONT_SIZE

VISA_ADDRESS = r'TCPIP0::192.168.0.80::inst0::INSTR'
BOOL2STRING = {True: "ON", False: "OFF"}

DISPLAY_FORMATS = Literal['MLOG', 'PHAS', 'UPH', 'POL']

class N5242A:

    def __init__(self, visa_address: str):
        self.address = visa_address
        self.instrument = None
        self.connect()

        self.idn = self.query('*IDN?')

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

    """ Measurements """

    def delete_measurements(self):
        self.write(r'CALCulate:PARameter:DELete:ALL')

    def create_measurement(self, name: str, matrix_element: str):
        self.write(f'CALCulate:PARameter:DEFine:EXTended \'{name}\', {matrix_element}')

    def bind_measurement_to_window(self, name: str):
        self.write(f'DISPlay:WINDow1:TRACe1:FEED \'{name}\'')

    def get_measurements(self):
        return self.query('CALCulate:PARameter:CATalog:EXTended?')

    def display_window(self):
        self.write(f'DISPlay:WINDow1:STATE ON')

    def set_measurement_format(self, display_format: DISPLAY_FORMATS):
        self.write(f'CALC:FORM {display_format}')

    def prepare_measurement(self, measurement_name: str = 'CH1_S24', matrix_element: str = 'S24',
                            display_format:DISPLAY_FORMATS = 'MLOG'):

        self.display_window()
        self.delete_measurements()
        self.create_measurement(name=measurement_name, matrix_element=matrix_element)
        self.bind_measurement_to_window(name=measurement_name)
        self.set_measurement_format(display_format=display_format)
        time.sleep(1)

    """ Data acquisition """

    def get_measurement_data(self):
        return self.instrument.query_binary_values('CALCulate:DATA? FDATA',
                                                   datatype='d',
                                                   is_big_endian=True,
                                                   container=np.ndarray)

    def get_complex_measurement_data(self):
        complex_data = self.instrument.query_binary_values('CALCulate:DATA? SDATA',
                                                           datatype='d',
                                                           is_big_endian=True,
                                                           container=np.ndarray)

        return complex_data[::2] + 1j * complex_data[1::2]

    def get_magnitude(self):
        complex_data = self.get_complex_measurement_data()
        magnitude = 20 * np.log10(np.abs(complex_data))
        return magnitude

    def get_phase(self, electrical_delay: float = None):

        complex_data = self.get_complex_measurement_data()
        frequencies = self.get_measurement_frequencies()

        if electrical_delay is None:
            phase = np.unwrap(np.angle(complex_data))
        else:
            phase_shifts = np.mod(2 * np.pi * frequencies * electrical_delay, 2 * np.pi)
            phase = np.unwrap(np.angle(complex_data, deg=False) + phase_shifts)

        return phase

    def get_measurement_frequencies(self):
        frequency_start = self.get_start_frequency_hz()
        frequency_stop = self.get_stop_frequency_hz()
        num_points = self.get_num_points()

        return np.linspace(frequency_start, frequency_stop, num_points)

    """ Power """

    def set_output_state(self, state: bool):
        self.write(f'OUTPut {BOOL2STRING[state]}')

    def get_output_state(self) -> bool:
        return bool(self.query('OUTPut?'))

    def set_power_dbm(self, power_dbm: float):
        self.write(f'SOUR:POW1 {power_dbm}dbm')

    def get_power_dbm(self) -> float:
        return float(self.query('SOUR:POW1?'))

    """ Sweep """

    def set_num_points(self, num_points: int):
        self.write(fr'SENSe1:SWEep:POINts {num_points}')

    def get_num_points(self):
        return int(float(self.query(f'SENSe1:SWEep:POINts?')))

    def set_start_frequency_hz(self, frequency_hz: int):
        self.write(f'SENSe1:FREQuency:START {int(frequency_hz)}hz')

    def get_start_frequency_hz(self) -> int:
        return int(float(self.query(f'SENSe1:FREQuency:STAR?')))

    def set_stop_frequency_hz(self, frequency_hz: int):
        self.write(f'SENSe1:FREQuency:STOP {int(frequency_hz)}hz')

    def get_stop_frequency_hz(self) -> int:
        return int(float(self.query(f'SENSe1:FREQuency:STOP?')))

    def set_center_frequency_hz(self, frequency_hz: int):
        self.write(f'SENSe1:FREQuency:CENTer {int(frequency_hz)}hz')

    def get_center_frequency_hz(self) -> int:
        return int(float(self.query(f'SENSe1:FREQuency:CENTer?')))

    def set_span_hz(self, span_hz: int):
        self.write(f'SENSe1:FREQuency:SPAN {int(span_hz)}hz')

    def get_sweep_duration(self):
        return float(self.query(r'SENSe1:SWEep:TIME?'))

    """ IF bandwidth and Averaging """

    def set_if_bandwidth(self, if_bandwidth_hz: int):
        self.write(f'SENSe1:BANDwidth {if_bandwidth_hz}')

    def set_average_state(self, state: bool):
        self.write(f'SENSe1:AVERage:STATe {BOOL2STRING[state]}')

    def set_num_averaging(self, num_averaging: int):
        self.write(f'SENSe1:AVERage:Count {num_averaging}')

    """ Electrical delay """

    def set_electrical_delay_ns(self, electrical_delay_ns: int):
        self.write(f'CALC1:CORR:EDEL:TIME {electrical_delay_ns}NS')


if __name__ == '__main__':
    rm = pyvisa.ResourceManager()
    vna = N5242A(visa_address=VISA_ADDRESS)

    # vna.prepare_measurement(display_format='MLOG')
    vna.set_power_dbm(power_dbm=-50)
    vna.set_electrical_delay_ns(electrical_delay_ns=0)
    vna.set_if_bandwidth(if_bandwidth_hz=200)
    vna.set_start_frequency_hz(int(2e9))
    vna.set_stop_frequency_hz(int(4e9))

    sweep_duration = np.ceil(vna.get_sweep_duration())
    print(f'sweep duration = {sweep_duration} seconds.')

    time.sleep(1)



    fig, axs = plt.subplots(1, 1, tight_layout=True)


    electrical_delay = 177e-9
    frequencies = vna.get_measurement_frequencies()
    axs.plot(frequencies / 1e9, vna.get_magnitude())
    # axs[1].plot(frequencies, vna.get_phase(electrical_delay=electrical_delay), color='black')

    axs.set_ylabel('S31 circulator', fontsize=FONT_SIZE)
    axs.set_xlabel('VNA frequency (GHz)', fontsize=FONT_SIZE)

    axs.grid()


    plt.show()
