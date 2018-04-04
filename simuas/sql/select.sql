SELECT b.pkuid, ST_Intersection(Buffer(a.geometry, 5), b.geometry) AS b_geom, ST_Intersection(Buffer(b.geometry, 5), a.geometry) as a_geom
    FROM test_lines AS a,
         test_lines AS b
    WHERE a.pkuid = 1
       AND ST_Crosses(Buffer(a.geometry, 5), b.geometry)