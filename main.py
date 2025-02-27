from qxp.experiments.autocat.ro_resonator_spectroscopy import RoResonatorSpectroscopy
from qxp.experiments.autocat.time_of_flight import TimeOfFlight

exp = TimeOfFlight().configure_and_run(do_update_db=False)
