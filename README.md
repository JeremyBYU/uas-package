# UAS Package Simulator


## Set up

1. Install python
2. Install pip
3. `pip install -r requirements.txt`


## Run

`python -m simuas.main` OR `python -m simuas.main debug`


## Keywords

* Package Center/Facility
    * A building where packages are located
    * The 'home' location for UAS
    * Has a repository of batteries, as well a charging stations where those batteries can be charged
* UAS
    * Has a battery, that decays over flight life
    * Carries packages

## Important Resources

* UAS
* Batteries
  * Are either fully charged (100%) or not (less than 100%)
  * Are put in the Battery Bank when fully charged (after being charged at the charging station)
* Battery Bank
  * Holds charged batteries. UAS request batteries from it.
* Charging Stations
    * Batteries request a charging station (configured to be infinite in this simulation) after returning from a flight


## Code Description

* `simuas` - This folder contains all the simulation code
  * `main.py` - Module that kicks off the simulation. Sets up simulation environment and runs replications and saves data.
  * `PackageFacility.py` - The brains of the package center simulator. Holds all the simulation logic and implicitly all the events
  * `Database.py` - UAS paths are lines that are recorded into a sqlite database (spatialite technically).  
  * `Util.py` and `helper.py` - Just utility and helper files.
* `notebooks` - Holds Jupyter notebook that analyzes the data that was saved from the simulation. Makes charts and so forht
* `requirements.txt` - holds all the modules required for running the simulation code.

