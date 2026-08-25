import time

from qxp.utils.units import units as u
from qxp.instruments.APUASYN20 import APUASYN20
from qxp.instruments.ASPIN20G import ASPIN20G
from qxp.instruments.BN103 import BN103


def initialize_apuasyn20(config, print_result=True):
    instrument = APUASYN20(visa_address=config['address'])
    instrument.set_frequency_hz(channel=config['channel'], frequency_hz=config['frequency'])
    instrument.set_power_dbm(channel=config['channel'], power_dbm=float(config['power']))
    instrument.set_output(channel=config['channel'], output=bool(config['output']))
    if print_result:
        if instrument.get_output(channel=config['channel']):
            print("    Output ON")
            print(f"    Power {instrument.get_power_dbm(channel=config['channel'])} dBm")
            print(f"    Frequency {instrument.get_frequency_hz(channel=config['channel'])} Hz")
        else:
            print("    Output OFF")
    instrument.close()


def initialize_aspin20(config, print_result=True):
    instrument = ASPIN20G(visa_address=config['address'])
    instrument.set_frequency_hz(frequency_hz=config['frequency'])
    instrument.set_power_dbm(power_dbm=float(config['power']))
    instrument.set_output(output=bool(config['output']))
    if print_result:
        if instrument.get_output():
            print("    Output ON")
            print(f"    Power {instrument.get_power_dbm()} dBm")
            print(f"    Frequency {instrument.get_frequency_hz()} Hz")
        else:
            print("    Output OFF")
    instrument.close()


# TODO implement voltage safety check
def initialize_bn103(config, print_result=True):
    if not config["output"]:
        turn_off_bn103(config)
        return

    instrument = BN103(ip=config['address'])
    instrument.set_output(
        module=config['module'],
        channel=config['channel'],
        state='on'
    )
    ramp_duration = instrument.ramp_voltage(
        module=config['module'],
        channel=config['channel'],
        value=config['voltage'],
        step_duration_ms=config['step_duration'] / u.ms,
        step_height_v=config['step_height']
    ) * u.ms
    if print_result:
        print(f"    Voltage ramping to {config['voltage']}V in {ramp_duration / u.s}s")
    time.sleep(ramp_duration / u.s)
    instrument.close()


def turn_off_apuasyn20(config):
    instrument = APUASYN20(visa_address=config['address'])
    instrument.set_output(channel=config['channel'], output=False)
    instrument.close()


def turn_off_aspin20(config):
    instrument = ASPIN20G(visa_address=config['address'])
    instrument.set_output(output=False)
    instrument.close()


def turn_off_bn103(config):
    instrument = BN103(ip=config['address'])
    ramp_duration = instrument.ramp_voltage(
        module=config['module'],
        channel=config['channel'],
        value=0.0,
        step_duration_ms=100,
        step_height_v=0.1
    ) * u.ms
    instrument.set_output(
        module=config['module'],
        channel=config['channel'],
        state='off'
    )
    print(f"[+] Voltage ramping to 0V in {ramp_duration / u.s}s, turning output OFF")
    time.sleep(ramp_duration / u.s)
    instrument.close()


def initialize_instruments_from_config(instruments_config):
    for name, config in instruments_config.items():
        print('[+] Initializing', name)
        match config['class']:
            case 'APUASYN20':
                initialize_apuasyn20(config)
            case 'ASPIN20G':
                initialize_aspin20(config)
            case 'BN103':
                initialize_bn103(config)
            case other:
                raise NotImplementedError(f"[!] {other} initialization is not implemented")
    print('[+] Done initializing instruments')


def turn_off_instruments_from_config(instruments_config):
    for name, config in instruments_config.items():
        print('[+] Turning off instruments', name)
        match config['class']:
            case 'APUASYN20':
                turn_off_apuasyn20(config)
            case 'ASPIN20G':
                turn_off_aspin20(config)
            case 'BN103':
                turn_off_bn103(config)
            case other:
                raise NotImplementedError(f"[!] {other} initialization is not implemented")
    print('[+] Done turning off instruments')


def get_instrument_by_name(name, instruments_config):
    config = instruments_config[name]
    match config['class']:
        case 'APUASYN20':
            instrument = APUASYN20(visa_address=config['address'])
        case 'ASPIN20G':
            instrument = ASPIN20G(visa_address=config['address'])
        case 'BN103':
            instrument = BN103(ip=config['address'])
        case other:
            raise NotImplementedError(f"[!] {other} instrument driver is not implemented")
    return instrument
