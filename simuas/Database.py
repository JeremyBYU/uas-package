"""Holds Database
"""

import random
import sqlite3

PACKAGE_DESTINATION_SEED = 10

RAND_PACKAGE = random.Random()
RAND_PACKAGE.seed(PACKAGE_DESTINATION_SEED)

DB_PATH = './data/uas_sim.sqlite'


CREATE_TABLE = """
SELECT InitSpatialMetaData();
CREATE TABLE paths  (
  uid TEXT NOT NULL,
  status TEXT);

SELECT AddGeometryColumn('paths', 'geometry', 3857, 'LINESTRING', 'XY');
"""

CREATE_TABLE_COLLISION = """
CREATE TABLE paths_collision  (
  a_uid TEXT NOT NULL,
  b_uid TEXT NOT NULL);

SELECT AddGeometryColumn('paths_collision', 'geometry', 3857, 'LINESTRING', 'XY');
"""

# LINE_STRING = "LINESTRING(:start_x :start_y, end_x end_y)"

RADIUS_BUFFER = 5

ADD_PATH = """
INSERT INTO paths(uid, status, geometry)
VALUES(:uid, :status, GeomFromText(:wkt, 3857))
"""

ADD_COLLISION = """
INSERT INTO paths_collision(a_uid, b_uid, geometry)
VALUES(:a_uid, :b_uid, GeomFromText(:wkt, 3857))
"""

INTERSECTION_PATH_SQL = """
SELECT b.uid as path_b_uid, ST_AsText(ST_Intersection(Buffer(a.geometry, :radius), b.geometry)) AS b_geom, ST_AsText(ST_Intersection(Buffer(b.geometry, :radius), a.geometry)) as a_geom
    FROM paths AS a,
         paths AS b
    WHERE a.uid = :path_a_uid
    AND a.uid != b.uid
    AND ST_Intersects(Buffer(a.geometry, :radius), b.geometry)
    AND NOT MBRWithin(ST_Intersection(Buffer(a.geometry, :radius), b.geometry), BuildMbr(:bbox_x_min,:bbox_y_min,:bbox_x_max,:bbox_y_max))
"""


CLEAR_PATHS = "DELETE FROM {}"

REMOVE_PATH = "DELETE FROM paths WHERE uid = :uid"

# INTERSECTION_PATH_SQL = """
# SELECT b.uid, ST_AsText(ST_Intersection(Buffer(a.geometry, 5), b.geometry)) AS a_geom, ST_AsText(ST_Intersection(Buffer(b.geometry, 5), a.geometry)) as b_geom
#     FROM paths AS a,
#          paths AS b
#     WHERE a.uid = :new_uid
#        AND ST_Crosses(Buffer(a.geometry, 5), b.geometry)
# """


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class Database(object):
    def __init__(self, db_path=DB_PATH, use_row=True):
        self.conn = sqlite3.connect(db_path, check_same_thread=True,)
        self.conn.enable_load_extension(True)
        self.conn.execute('SELECT load_extension("mod_spatialite")')
        self.conn.row_factory = sqlite3.Row if use_row else dict_factory

        if db_path == ':memory:':
            self.create_in_memory_db()
        
        # self.conn.executescript(CREATE_TABLE_COLLISION)
        # self.conn.commit()

    def create_in_memory_db(self):
        self.conn.executescript(CREATE_TABLE)

        self.conn.executescript(CREATE_TABLE_COLLISION)
        self.conn.commit()
    
    
    def get_path_intersection(self, path_uid, bbox):
        sql = INTERSECTION_PATH_SQL
        curs = self.conn.cursor()
        res = curs.execute(sql, {'path_a_uid': path_uid, 'bbox_x_min': bbox[0], 'bbox_y_min': bbox[1], 'bbox_x_max': bbox[2], 'bbox_y_max': bbox[3], 'radius': RADIUS_BUFFER})
        rows = res.fetchall()
        curs.close()
        return rows

    def insert_path(self, uas):
        sql = ADD_PATH
        path_line = uas.path
        query_params = {'uid': uas.uid, 'status': 'flight', 'wkt': path_line.to_wkt()}
        curs = self.conn.cursor()
        curs.execute(sql, query_params)
        # self.conn.commit()
    def insert_collision(self, a_uid, a_wkt, b_uid, b_wkt):
        sql = ADD_COLLISION
        query_params = {'a_uid': a_uid, 'b_uid': b_uid, 'wkt': a_wkt}
        curs = self.conn.cursor()
        curs.execute(sql, query_params)

        query_params = {'a_uid': a_uid, 'b_uid': b_uid, 'wkt': b_wkt}
        curs.execute(sql, query_params)
        self.conn.commit()

    def clear_paths(self, table='paths'):
        curs = self.conn.cursor()
        curs.execute(CLEAR_PATHS.format(table))

    def remove_path(self, uid):
        curs = self.conn.cursor()
        curs.execute(REMOVE_PATH, {'uid': uid})





