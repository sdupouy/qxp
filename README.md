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
- `cd` where you want to create your project directory
- `qxp-create-project <your-project-name>`

## Running experiments
Write your experiments in the `/experiments` directory.  
An experiment is a class that inherits from `qxp.core.BaseQuaExperiment`.

You can then import your experiment classes as Python modules like this:  
`from qxp.experiments.your_experiment import YourExperiment`.

Run your experiment like this:  
```python
exp = YourExperiment()
exp.configure_and_run()
```

## To launch the web panel:
- Run `qxp-start-webpanel` in the terminal from within the project directory
- Open a web browser and go to http://127.0.0.1:8000 

## TODO list
- fill up templates for the measurement database
  - cooldown_list
  - cooldown_detail
- use katex to render parameter latex in the web panel
- handle missing optional fields on models (e.g. pictures)
- make all scripts (e.g. bootstrap) local so that the panel works well offline
- make exp runs markable by a star
- button to edit the comments on-page
- add filters on the measurements and exp_run list views
- matplotlib plots of the parameter's evolution
- implement other experiments
    - readout duration optimization
    - readout weights optimization
    - ro resonator spectroscopy lo sweep
    - transmon spectroscopy lo sweep
    - Rabi chevron
    - T1
    - Ramsey
    - T2 echo