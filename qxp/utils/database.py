from qxp.measurement_db.core.models import Measurement, Cooldown
from qxp.config import CURRENT_CHIP


def current_cooldown():
    """ Fetch the current cooldown from the database. """
    if CURRENT_CHIP:
        return Cooldown.objects.filter(chip__name=CURRENT_CHIP).latest('datetime')
    return Cooldown.objects.latest('datetime')


def current_chip():
    """ Fetch the current chip from the database. """
    return current_cooldown().chip


def fetch_last_measured_value(parameter_name):
    """ Fetch last measured value from database.
    Args:
        parameter_name: The name of the parameter.
    """
    try:
        measurement = Measurement.objects.filter(
            experiment_run__cooldown__chip=current_chip(),
            parameter__name=parameter_name
        ).order_by('experiment_run__datetime').last()
    except Measurement.DoesNotExist:
        return None
    return measurement.value
