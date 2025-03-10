# Quantum Experimentation Platform (qxp)

**qxp** is a framework written in Python for developing quantum experiments on a Quantum Machines setup, with
automation and reproducibility in mind.

This software aims at providing a way to:
- easily automatize measurements on a Quantum Machines setup
- efficiently keep track of experimental data and the setup that was used for acquisition
- manage and display measured data through a web interface (based on Django)
- interact with common lab instruments
- enforce organized coding patterns and directory structure

## Installation
To install qxp in editable mode, run:
- `pip install -e .`

Then:
- `cd` into the project root
- `qxp-create-project <your-project-name>`

To launch the webpanel:
- `python manage.py runserver`

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