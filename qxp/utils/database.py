from qxp.config import CURRENT_CHIP
from qxp.measurement_db.core.models import Measurement, Cooldown
from qxp.utils.units import try_to_match_units


def current_cooldown():
    """ Fetch the current cooldown from the database. """
    if CURRENT_CHIP:
        return Cooldown.objects.filter(chip__identifier=CURRENT_CHIP).latest('datetime')
    return Cooldown.objects.latest('datetime')


def current_chip():
    """ Fetch the current chip from the database. """
    return current_cooldown().chip


def fetch_last_measured_value(parameter_ident, unit=None):
    """ Fetch last measured value from database.
    Args:
        parameter_ident (string): The identifier of the parameter.
        unit (string): The target unit.
    """
    measurement = Measurement.objects.filter(
        experiment_run__cooldown__chip=current_chip(),
        parameter__identifier=parameter_ident
    ).order_by('experiment_run__datetime').last()
    if measurement:
        if unit is not None:
            multiplier = try_to_match_units(measurement.parameter.unit, unit)
        else:
            multiplier = 1
        return measurement.value * multiplier
