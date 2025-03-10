# Quantum Experimentation Platform (qxp)

This software aims at providing:
- a way to automatize measurements on a Quantum Machines setup
- a way to efficiently keep track of experimental data and the setup that was used for acquisition
- a way to manage and display measured data through a web interface

## Installation
- `cd` into the project root
- `pip install . -e`
- `python manage.py migrate`

### To launch the web interface:
- `python manage.py runserver`
- open a web browser and go to http://127.0.0.1:8000 

## TODO list
- fill up templates for the measurement database
- improve the admin panel
- implement other experiments
    - readout duration optimization
    - readout weights optimization
    - ro resonator spectroscopy lo sweep
    - transmon spectroscopy lo sweep
    - Rabi chevron
    - T1
    - Ramsey
    - T2 echo