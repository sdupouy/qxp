from qxp.config import CURRENT_CHIP
from qxp.measurement_db.core.models import Measurement, Cooldown


def current_cooldown():
    """ Fetch the current cooldown from the database. """
    if CURRENT_CHIP:
        return Cooldown.objects.filter(chip__identifier=CURRENT_CHIP).latest('datetime')
    return Cooldown.objects.latest('datetime')


def current_chip():
    """ Fetch the current chip from the database. """
    return current_cooldown().chip


def fetch_last_measured_value(parameter_ident):
    """ Fetch last measured value from database.
    Args:
        parameter_ident: The identifier of the parameter.
    """
    measurement = Measurement.objects.filter(
        experiment_run__cooldown__chip=current_chip(),
        parameter__identifier=parameter_ident
    ).order_by('experiment_run__datetime').last()
    if measurement:
        return measurement.value
