""" Driver for BILT BN103 unit.
For BE2101 cards, setting the channel does not change anything.
"""

import socket
from typing import Optional, Literal, Tuple
from functools import wraps
import time
import numpy as np


def access(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        self.open()
        result = func(*args, **kwargs)
        self.close()
        return result
    return wrapper


def str2command(command_string: str):
    return bytes(command_string + '\n', 'ascii')


class BN103:
    def __init__(self, ip: str, port: int = 5025):
        self.ip = ip
        self.port = port
        self.client: Optional[socket.socket] = None
        self._is_open = 0

    def open(self):
        if not self._is_open:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((self.ip, self.port))
        self._is_open += 1

    def close(self):
        self._is_open -= 1
        if self._is_open == 0:
            self.client.close()

    def switch_channel(self, module: int, channel: int):
        self.client.send(str2command(f'i{module};c{channel}'))
        time.sleep(0.1)

    @access
    def verify_connection(self) -> str:
        self.client.send(str2command('*idn ?'))
        response = self.client.recv(1024)
        return response.decode("utf-8")

    @access
    def reset_rack(self) -> None:
        self.client.send(str2command('*rst'))
        time.sleep(5)

    @access
    def set_output(self, module: int, channel: int, state: Literal['on', 'off']) -> None:
        self.switch_channel(module, channel)
        self.client.send(str2command(f'output {state}'))

    @access
    def set_voltage(self, module: int, channel: int, value: float) -> None:
        self.switch_channel(module, channel)
        self.client.send(str2command(f'volt {value}'))
        self.client.send(str2command(f'trig:input:init'))
        time.sleep(0.1)

    @access
    def get_voltage(self, module: int, channel: int) -> float:
        self.switch_channel(module, channel)
        self.client.send(str2command(f'meas:volt ?'))
        response = self.client.recv(4096)
        return float(response.decode("utf-8"))

    @access
    def get_current(self, module: int, channel: int) -> float:
        self.switch_channel(module, channel)
        self.client.send(str2command(f'meas:curr ?'))
        response = self.client.recv(4096)
        return float(response.decode("utf-8"))

    @access
    def set_voltage_range(self, module: int, channel: int, value: Literal['low', 'high']) -> None:
        # low 1 : 1.2 V
        # high 2 : 12 V
        if value == 'low':
            volt_range = 1
        elif value == 'high' or value == 0.01:
            volt_range = 2
        else:
            raise Exception('Invalid voltage range value.')
        self.set_output(module, channel, 'off')
        self.client.send(str2command(f'volt:rang:auto 0'))
        self.client.send(str2command(f'volt:rang {volt_range}'))
        self.set_output(module, channel, 'on')

    def set_voltage_limit(self, value: float):
        pass

    @access
    def get_limit(self, module: int, channel: int, value: float) -> None:
        pass

    @access
    def set_mode(self, module: int, channel: int, mode: Literal['exp', 'ramp', 'stair']) -> None:
        self.switch_channel(module, channel)
        self.client.send(str2command(f'trig:input exp'))
        time.sleep(0.1)
        self.client.send(str2command(f'trig:input {mode}'))
        time.sleep(0.1)

    @access
    def set_staircase_parameters(self, module: int, channel: int, step_duration_ms: float, step_height: float) -> None:
        # step duration [ms]
        # step width [V]
        self.switch_channel(module, channel)
        step_duration_ms = np.clip(step_duration_ms, a_min = 10, a_max = 60000)
        self.client.send(str2command(f'volt:step:width {step_duration_ms} ;: volt:step:ampl {step_height}'))
        time.sleep(0.1)

    @access
    def set_slope(self,  module: int, channel: int, value: float) -> None:
        self.switch_channel(module, channel)
        self.client.send(str2command(f'volt:slop {value}'))

    @access
    def ramp_voltage(self, module: int, channel: int, value: float, step_duration_ms, step_height_v) -> float:
        self.set_mode(module, channel, 'stair')
        self.set_staircase_parameters(module, channel, step_duration_ms=step_duration_ms, step_height=step_height_v)

        current_voltage = self.get_voltage(module=module, channel=channel)
        voltage_difference = np.abs(value - current_voltage)
        num_steps = int(voltage_difference / step_height_v)
        ramp_duration_ms = num_steps * step_duration_ms

        self.set_voltage(module, channel, value)
        time.sleep(0.1)  # TODO: check whether necessary
        self.client.send(str2command(f'trig:input:init'))
        return ramp_duration_ms


if __name__ == '__main__':
    bn103 = BN103('192.168.0.136')
    bn103.open()
    ramp_duration = bn103.ramp_voltage(module=1, channel=1, value=0.0, step_duration_ms=200, step_height_v=0.010)
    print(f'{ramp_duration / 1e3 :.2f} seconds')
