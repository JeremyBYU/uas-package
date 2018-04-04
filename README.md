## UAS Package Simulator


### Keywords

* Package Location
    * A building where packages are located
    * The 'home' location for UAS
    * Has a repository of batteries, as well a charging stations where those batteries can be charged
* UAS
    * Has a battery, that decays over flight life
    * Carries packages

Important Resources

* UAS
    * State - Flight, Package Center Waiting for Package, Package Center Waiting for Battery Change
* UAS Package Locaton Ready Fleet
    * A resource where UAS are ready to be assigned a package and destination
* Battery Bank (N Batteries)
  * UAS requests battery from Battery Bank
  * Must wait if battery not available



  Code Ideas -

Battery Bank should be a Resource
  - Your request from it
  - If it has capacity it serves you a fully charged batter, if not you must wait
Batter Charging Station
  - Waits for an event 


What info do you want?

Average Inventory of UAS available - Histograms as well
Average Inventory of Batteries available - Histograms as well
How many times did battery go down below safety level?
How many times did we possibly have collisions?
Service time for packages?




  Interrupt flight

  ```python
>>> class EV:
...     def __init__(self, env):
...         self.env = env
...         self.drive_proc = env.process(self.drive(env))
...
...     def drive(self, env):
...         while True:
...             # Drive for 20-40 min
...             yield env.timeout(randint(20, 40))
...
...             # Park for 1 hour
...             print('Start parking at', env.now)
...             charging = env.process(self.bat_ctrl(env))
...             parking = env.timeout(60)
...             yield charging | parking
...             if not charging.triggered:
...                 # Interrupt charging if not already done.
...                 charging.interrupt('Need to go!')
...             print('Stop parking at', env.now)
...
...     def bat_ctrl(self, env):
...         print('Bat. ctrl. started at', env.now)
...         try:
...             yield env.timeout(randint(60, 90))
...             print('Bat. ctrl. done at', env.now)
...         except simpy.Interrupt as i:
...             # Onoes! Got interrupted before the charging was done.
...             print('Bat. ctrl. interrupted at', env.now, 'msg:',
...                   i.cause)
...
>>> env = simpy.Environment()
>>> ev = EV(env)
  ```