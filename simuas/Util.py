
import random
import math
import re
from enum import Enum
import numpy as np
from recordclass import recordclass


PACKAGE_DESTINATION_SEED = 10
PACKAGE_WEIGHT_SEED = 12

RAND_PACKAGE = np.random.RandomState()
RAND_PACKAGE.seed(PACKAGE_DESTINATION_SEED)

RAND_WEIGHT = np.random.RandomState()
RAND_WEIGHT.seed(PACKAGE_WEIGHT_SEED)


MAX_WEIGHT = 3


BAT_TO_DIST = [.01058, .01163, .01292, .01452]


class UasState(Enum):
    wait_package = 1
    flight = 2
    wait_battery_change = 3


# Create a mutable named tuples for Package, Batter, and UAS
# This is like a class but more lightweight and efficient
Package = recordclass('Package', [
    'uid', 'center_uid', 'count', 'creation_time', 'destination',  'weight', 'start_time', 'uas_wait', 'delivery_wait', 'total_wait'])
Package.__new__.__defaults__ = (None,) * len(Package._fields)


Battery = recordclass('Battery', ['uid', 'center_uid', 'charge'])
Battery.__new__.__defaults__ = (None,) * len(Battery._fields)

Uas = recordclass('Uas', ['uid', 'center_uid', 'state',
                          'battery', 'package', 'path', 'path_start_time'])
Uas.__new__.__defaults__ = (None,) * len(Uas._fields)

Point = recordclass('Point', ['x', 'y'])

LINE_STRING = "LINESTRING({} {}, {} {})"


class Line(object):
    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end
        self.vector = np.array([end.x - start.x, end.y - start.y])
        self.length = np.linalg.norm(self.vector)
        # If we have the zero vector then we dont need to normalize
        if self.length > .0001:
            self.vector = self.vector / self.length

    def along(self, distance):
        du = self.vector * distance
        x = self.start.x + du[0]
        y = self.start.y + du[1]
        return Point(x, y)

    def to_wkt(self):
        return LINE_STRING.format(self.start.x, self.start.y, self.end.x, self.end.y)

    def __str__(self):
        self.__repr__()

    def __repr__(self):
        return "({:.1f}, {:.1f}) -> ({:.1f}, {:.1f})".format(self.start.x, self.start.y, self.end.x, self.end.y)

    @staticmethod
    def from_wkt(wkt):
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", wkt)
        if len(numbers) == 4:
            return Line(Point(float(numbers[0]), float(numbers[1])), Point(float(numbers[2]), float(numbers[3])))
        else:
            return None


def get_package_destination(center, radius, rand_stream=RAND_PACKAGE):
    """Gets a random point from a uniform disc around a package center
    
    Arguments:
        center {Point} -- The center of the package center
        radius {[type]} -- The max radius
    
    Keyword Arguments:
        rand_stream {random_generator} -- random stream (default: {RAND_PACKAGE})
    """
    rand_r = rand_stream.uniform(0, 1)
    rand_theta = rand_stream.uniform(0, 2 * math.pi)
    x = center.x + radius * math.sqrt(rand_r) * math.cos(rand_theta)
    y = center.y + radius * math.sqrt(rand_r) * math.sin(rand_theta)
    return Point(x, y)


def random_package_point(bounds):
    x_point = RAND_PACKAGE.uniform(bounds[0], bounds[2])
    y_point = RAND_PACKAGE.uniform(bounds[1], bounds[3])
    return Point(x_point, y_point)


def get_package_weight(rand_stream=RAND_WEIGHT):
    """Gets a package weight, between 1-3
    
    Keyword Arguments:
        rand_stream {random_generator} -- The random stream(default: {RAND_WEIGHT})
    """
    # print(MAX_WEIGHT)
    # import pdb
    # pdb.set_trace()
    weight = rand_stream.randint(1, MAX_WEIGHT + 1)
    # print("Weight: ", weight)
    return weight
