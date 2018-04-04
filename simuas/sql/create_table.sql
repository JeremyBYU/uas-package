CREATE TABLE paths  (
  uid TEXT NOT NULL,
  status TEXT);

SELECT AddGeometryColumn('paths', 'geometry', 3857, 'LINESTRING', 'XY');