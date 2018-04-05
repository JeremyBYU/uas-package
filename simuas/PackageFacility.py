"""Encapsulates logic for a package facility
"""
import sys
import logging
from uuid import uuid4
import random
from pprint import pprint as pp
import simpy
from simuas.helper import MonitoredStore, QueueCount, condense


from simuas.Util import Package, Battery, Uas, UasState, Point, Line, get_package_destination, get_package_weight, BAT_TO_DIST

DEMAND_SEED = 1
BATTERY_SERVICE_SEED = 100

# Conversion from meters/sec to meters/min
MS_TO_MM = 60


# This holds are random number generators
# Needed when we do replications and dont want to reset the seed
# on the next replication
RANDOM_GENERATORS = {}

MAX_SIM_TIME = 12 * 60

# RADIUS around package center which no collision can happen
BBOX_PACKAGE_CENTER = 100


def get_random_gen(seed):
    generator = RANDOM_GENERATORS.get(seed)
    if generator is None:
        generator = random.Random()
        generator.seed(seed)
        RANDOM_GENERATORS[seed] = generator
    return generator


def create_error(time, err_type, uas, other=''):
    return {'time': time, 'err_type': err_type, 'uas': uas, 'other': other}


class PackageFacility(object):
    def __init__(self, env, uid, db, bounds, center, lambda_demand=1, mu_battery=80, battery_capacity=100, uas_capacity=15, uas_speed=7.5, replacement_time=2, safety_battery_level=20, demand_stop_time=MAX_SIM_TIME):
        self.env = env      # global simulation environment
        self.uid = uid      # unique identifying number of package facility
        self.bounds = bounds  # bounding box of service TODO change to radius?
        # the center location of this package facility
        self.center = Point(center[0], center[1])
        self.bbox_center = [self.center.x - BBOX_PACKAGE_CENTER, self.center.y - BBOX_PACKAGE_CENTER,
                            self.center.x + BBOX_PACKAGE_CENTER, self.center.y + BBOX_PACKAGE_CENTER]
        self.db = db        # database connection
        self.lambda_demand = lambda_demand  # mean of demand
        self.mu_battery = mu_battery       # mean of battery service
        self.battery_capacity = battery_capacity
        self.uas_capacity = uas_capacity
        self.uas_speed = uas_speed
        self.replacement_time = replacement_time
        self.safety_battery_level = safety_battery_level
        self.demand_stop_time = demand_stop_time
        # Our Resources
        self.battery_bank = MonitoredStore(env)
        self.uas_bank = MonitoredStore(env)
        # Queue Length stats
        self.uas_queue = QueueCount(self.env)
        self.charging_stations = QueueCount(self.env)
        # A list to hold all packages created, might not be necessary
        self.packages = []

        # initialize our resources
        self.init_battery()
        self.uas_set = {}
        env.process(self.init_uas())

        # Create independent random streams
        self.demand_rand = get_random_gen(DEMAND_SEED * self.uid)

        # Hash Table to hold events that *may* need to be canceled
        self.package_process = dict()
        # logging.debug(self.battery_bank.print_stats())

        self.errors = []

        env.process(self.demand_source())
        env.process(self.report_stats())

    def data_package(self):
        return {
            'charging_stations': condense(self.charging_stations),
            'uas_queue': condense(self.uas_queue),
            'battery_bank': condense(self.battery_bank),
            'uas_bank': condense(self.uas_bank),
            'packages': self.packages,
            'errors': self.errors
        }

    def report_stats(self, interval=10):
        yield self.env.timeout(interval)
        while self.env.now < self.demand_stop_time:
            avg_battery_bank_level = self.battery_bank.avg_value
            avg_uas_bank_level = self.uas_bank.avg_value
            logging.info('Sim Time: %.2f. Avg Stats - Battery bank level: %.1f, UAS bank level: %.1f',
                         self.env.now, avg_battery_bank_level, avg_uas_bank_level)
            # self.battery_bank.print_stats()
            # self.uas_bank.print_stats()
            yield self.env.timeout(interval)

    def init_uas(self):
        for i in range(self.uas_capacity):
            battery_req = self.battery_bank.get()
            battery = yield battery_req
            uas = Uas(uuid4().hex, self.uid, UasState.wait_package, battery)
            self.uas_set[uas.uid] = uas
            self.uas_bank.put(uas)

    def init_battery(self):
        for i in range(self.battery_capacity):
            battery = Battery(uuid4().hex, self.uid, 100)
            self.battery_bank.put(battery)

    # def createPath(self, uas, package):
    #     path = Line(self.center, )
    #     uas.package = package

    def replace_battery(self, uas):
        # Request a fully charged battery from the battery bank, wait for it
        with self.battery_bank.get() as battery_req:
            logging.debug(
                'Sim Time: %.2f. Requesting replacement battery for UAS (%s)', self.env.now, uas.uid)
            battery = yield battery_req
            uas.battery = battery
            uas.path = None
            uas.state = 'waiting'

            # Deterministic Replacement Time
            yield self.env.timeout(self.replacement_time)

            logging.debug(
                'Sim Time: %.2f. Received replacement battery (%s) for UAS (%s) ', self.env.now, battery.uid, uas.uid)
            self.uas_bank.put(uas)

    def charge_battery(self, battery: Battery):
        # Assume infinite charging stations, use the queue to keep track of how many are used at any given time
        time_to_charge = (100-battery.charge) / 100 * self.mu_battery
        logging.debug(
            'Sim Time: %.2f. Beggining to charge battery (%s). From %.1f%% to 100%%. %.1f mins', self.env.now, battery.uid, battery.charge, time_to_charge)

        self.charging_stations.add()
        yield self.env.timeout(time_to_charge)
        self.charging_stations.remove()

        battery.charge = 100
        self.battery_bank.put(battery)

    def replace_battery_and_recharge(self, uas):
        self.env.process(self.charge_battery(uas.battery))
        self.env.process(self.replace_battery(uas))

    def handle_package(self, package):
        # Request a UAS that is fully charged
        with self.uas_bank.get() as uas_req:
            before_uas_time = self.env.now
            self.uas_queue.add()            # increment uas queue
            uas = yield uas_req
            self.uas_queue.remove()         # decrement uas queue

            logging.debug(
                'Sim Time: %.2f. UAS (%s) ready for delivery of package (%s)', self.env.now, uas.uid, package.uid)

            package.start_time = self.env.now
            package.uas_wait = self.env.now - before_uas_time
            uas.package = package
            uas.path = Line(self.center, package.destination)
            uas.path_start_time = self.env.now
            uas.state = 'flight_package'
            self.db.insert_path(uas)

            # Check Collision
            self.check_collision(uas)

            # Wait for arrival at package destination
            eta = uas.path.length / (self.uas_speed * MS_TO_MM)
            yield self.env.timeout(eta)

            logging.debug(
                'Sim Time: %.2f. UAS (%s) delivered package. Going home', self.env.now, uas.uid)

            # We have successfully arrived at our destination!
            # Deplete the battery
            uas.battery.charge -= uas.path.length * \
                BAT_TO_DIST[package.weight]

            # Deliver Package
            package.delivery_wait = self.env.now - uas.path_start_time
            package.total_wait = self.env.now - package.creation_time
            uas.package = None
            # Plan to next destination (back to home), remove old path
            uas.path = Line(package.destination, self.center)
            uas.path_start_time = self.env.now
            uas.state = 'flight_home'
            self.db.remove_path(uas.uid)
            self.db.insert_path(uas)

            # Check Collision
            self.check_collision(uas)

            # Wait for arrival at package center
            yield self.env.timeout(eta)

            # We have successfully arrived at package center
            # Deplete the battery, no load
            uas.battery.charge -= uas.path.length * \
                BAT_TO_DIST[0]
            # Remove old path
            self.db.remove_path(uas.uid)

            if(uas.battery.charge < self.safety_battery_level):
                logging.error('Sim Time: %.2f. UAS (%s) battery (%s) below safety level! Level %.1f',
                              self.env.now, uas.uid, uas.battery.uid, uas.battery.charge)
                self.errors.append(create_error(
                    self.env.now, 'battery_low', uas.uid, uas.battery.charge))

            logging.debug(
                'Sim Time: %.2f. UAS (%s) delivered package (%s). Now at package center with battery %.1f', self.env.now, uas.uid, package.uid, uas.battery.charge)

            # Replace battery and recharge
            self.replace_battery_and_recharge(uas)

    def check_collision(self, uas):
        path_intersections = self.db.get_path_intersection(
            uas.uid, self.bbox_center)
        if len(path_intersections) > 0:
            for path in path_intersections:
                result = self.check_path_time_collision(uas, path)
                if result:
                    # self.db.conn.commit()
                    logging.error('Sim Time: %.2f. UAS (%s) collides with UAS (%s)!',
                                  self.env.now, uas.uid, path['path_b_uid'])
                    self.errors.append(create_error(
                        self.env.now, 'uas_collision', uas.uid, path['path_b_uid']))

    def check_path_time_collision(self, uas, path):
        """Check for a possible collision with a UAS and the *possible* collision from the path variable
        A collision is when two UAS are near eachother in SPACE and TIME
        Arguments:
            uas {[UAS]} -- The UAS that just planned a path
            path {path_result} -- This is a result from a SQL query that says two lines (paths) intersect around a buffered radius
        """
        uas_a = uas
        uas_b = self.uas_set[path['path_b_uid']]  # possibel offending UAS

        # SPACE
        # These are sub lines of the respective uas paths that could have a collision
        uas_a_intersection = Line.from_wkt(path['a_geom'])
        uas_b_intersection = Line.from_wkt(path['b_geom'])
        # TIME
        # Determine at what time interval the UAS will be at these sections of possible collisions
        interval_a = self.time_bounds(uas_a, uas_a_intersection)
        interval_b = self.time_bounds(uas_b, uas_b_intersection)

        return interval_a[0] <= interval_b[1] and interval_b[0] <= interval_a[1]

    def time_bounds(self, uas, uas_intersection):
        # Get the beggining and ending lines
        l1 = Line(uas.path.start, uas_intersection.start)
        l2 = Line(uas.path.start, uas_intersection.end)
        if uas.state == 'flight_package':
            # We are flying torwards the package
            # distance to travel to get to the collision interval
            l1_dist = max(l1.length, BBOX_PACKAGE_CENTER)
            l2_dist = l2.length

        else:
            # we are flying home
            # distance to travel to get to the collision interval
            l1_dist = l1.length
            l2_dist = min(l2.length, uas.path.length - BBOX_PACKAGE_CENTER)

        time_lower = l1_dist / \
            (self.uas_speed * MS_TO_MM) + uas.path_start_time
        time_upper = l2_dist / \
            (self.uas_speed * MS_TO_MM) + uas.path_start_time

        return (time_lower, time_upper)

    def demand_source(self):
        """Process that creates new package demand"""
        yield self.env.timeout(.1)  # add a .1 minute delay, just to make sure all our initialization is done
        while True:
            time = self.env.now
            if time > self.demand_stop_time:
                break
            package = Package(uuid4().hex, self.uid,
                              len(self.packages), self.env.now)

            # set the random destination and weight
            package.destination = get_package_destination(self.bounds)
            package.weight = get_package_weight()

            logging.debug(
                'Sim Time: %.2f. New package demand at %.2f. Package uid: %s', self.env.now, time, package.uid)
            self.packages.append(package)
            # Launch new process independent of demand
            package_handling_process = self.handle_package(package)
            # record the process handler in case we need to cancel it later
            self.package_process[package.uid] = self.env.process(
                package_handling_process)
            # Schedule next event
            t = self.demand_rand.expovariate(1.0 / self.lambda_demand)
            yield self.env.timeout(t)
