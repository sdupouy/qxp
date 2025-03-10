from qxp.utils.save import fetch_last_from_db


def auto_set_exp_config(exp_config):
    if (m := fetch_last_from_db('ro_resonator_resonance_freq')) is not None:
        exp_config['ro_resonator']['resonance_freq'] = m.value
        exp_config['ro_resonator']['ro_pulse_freq'] = m.value

    if (m := fetch_last_from_db('ro_pulse_freq')) is not None:
        exp_config['ro_resonator']['ro_pulse_freq'] = m.value

    if (m := fetch_last_from_db('transmon_resonance_freq')) is not None:
        exp_config['transmon']['resonance_freq'] = m.value


def auto_set_instruments_config(instruments_config, exp_config):
    ro_resonator_lo_freq = (
            exp_config['ro_resonator']['ro_pulse_freq']
            - exp_config['ro_resonator']['sideband'] * exp_config['ro_resonator']['i_freq']
    )
    instruments_config['ro_resonator_lo']['frequency'] = ro_resonator_lo_freq

    transmon_lo_freq = (
            exp_config['transmon']['resonance_freq']
            - exp_config['transmon']['sideband'] * exp_config['transmon']['i_freq']
    )
    instruments_config['transmon_lo']['frequency'] = transmon_lo_freq
