"""Main Module for UAS Simulator
"""
import sys
import logging
import simpy
import pickle
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
            'bounds': [0,  0, 5000, 7000],
            'center': [2500,3500]
        }
    ]
}


class UASSimulator(object):
    def __init__(self, env, options):
        self.db = Database(':memory:')
        self.db.clear_paths()
        self.env = env

        # Single Package Facility
        kw_dict = dict(options['package_facilities_global'])
        kw_dict.update(options['package_facilities'][0])
        self.pfs = PackageFacility(env, 1, self.db, **kw_dict)
        ## Multiple Package Facility
        # self.pfs = []
        # for i, facility in enumerate(options['package_facilities']):
        #     kw_dict = dict(options['package_facilities_global'])
        #     kw_dict.update(facility)
        #     self.pfs.append(PackageFacility(env, i+1, self.db, **kw_dict))

    
    def print_loc_stats(self, i):
        pf = self.pfs[i]
        battery_bank_capacity = pf.battery_bank.capacity
        logging.info('Package Facility %s: Battery bank level - %.1f', i, battery_bank_capacity)

    def run_stats(self):
        print("\nSummary Stats:")
        for i, pf in enumerate(self.pfs):
            battery_bank_capacity = len(pf.battery_bank.items)
            uas_bank_capacity = len(pf.uas_bank.items)
            logging.info('Package Facility %s: Battery bank level - %.1f, UAS bank level - %.1f', i, battery_bank_capacity, uas_bank_capacity)
            print("Battery Stats")
            pf.battery_bank.print_stats()
            print("UAS Stats")
            pf.uas_bank.print_stats()
    
    def run(self):
        self.env.run(MAX_SIM_TIME)
        # self.data_pfs = [pacakge_facility.data_package()  for pacakge_facility in self.pfs]
        self.data_pfs = self.pfs.data_package()




def main():
    print('Begin Execution')
    if len(sys.argv) > 1:
        if sys.argv[1] == 'info':
            logging.basicConfig(level=logging.INFO)
        elif sys.argv[1] == 'debug':
            logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARN)

    replications = []
    for i in range(N_REPLICATIONS):
        env = simpy.Environment()
        simulator = UASSimulator(env, OPTIONS)
        simulator.run()
        replications.append(simulator.data_pfs)

    pickle.dump( replications, open( "./data/repl_results.p", "wb" ) )
    simulator.db.conn.commit()


if __name__ == '__main__':
    main()
