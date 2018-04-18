"""Main Module for UAS Simulator
"""
import sys
import logging
import pickle
import simpy
from simuas.PackageFacility import PackageFacility
from simuas.Database import Database


MAX_SIM_TIME = 12 * 60
N_REPLICATIONS = 30

OPTIONS = {
    'package_facilities_global': {
        'battery_capacity': 100
    },
    'package_facilities': [
        {
            'lambda_demand': 1.28,
            'radial_bounds': 2750,
            'center': [-8237051.3, 4971994.1],
            'uas_capacity': 17
        },
        {
            'lambda_demand': 1.28,
            'radial_bounds': 2750,
            'center': [-8236999.70268, 4973094.16743],
            'uas_capacity': 17
        }
    ]
}


class UASSimulator(object):
    def __init__(self, env, options):
        self.db = Database(':memory:')
        # self.db = Database()
        self.db.clear_paths('paths')
        self.db.clear_paths('paths_collision')
        self.env = env

        # Single Package Facility
        # kw_dict = dict(options['package_facilities_global'])
        # kw_dict.update(options['package_facilities'][0])
        # self.pfs = PackageFacility(env, 1, self.db, **kw_dict)
        # Multiple Package Facility
        self.pfs = []
        for i, facility in enumerate(options['package_facilities']):
            kw_dict = dict(options['package_facilities_global'])
            kw_dict.update(facility)
            self.pfs.append(PackageFacility(env, i+1, self.db, **kw_dict))


    def run(self):
        self.env.run(MAX_SIM_TIME) # stop at max simulation time
        self.data_pfs = [pf.data_package() for pf in self.pfs] # create data package for each package center
        self.db.conn.commit()
        self.db.conn.close()


def main():
    print('Begin Execution')
    if len(sys.argv) > 1:
        if sys.argv[1] == 'info':
            logging.basicConfig(level=logging.INFO)
        elif sys.argv[1] == 'debug':
            logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARN)

    # Store replication data
    replications = []
    for i in range(N_REPLICATIONS):
        env = simpy.Environment()
        simulator = UASSimulator(env, OPTIONS)
        simulator.run()
        replications.append(simulator.data_pfs)

    pickle.dump(replications, open("./data/repl_results_dual.p", "wb"))


if __name__ == '__main__':
    main()
