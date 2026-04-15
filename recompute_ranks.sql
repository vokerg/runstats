-- recompute_ranks.sql
BEGIN;

-- all-distance ranks
DROP TABLE IF EXISTS temp.rank_all;
CREATE TEMP TABLE rank_all AS
SELECT run_no,
       RANK() OVER (PARTITION BY distance_km ORDER BY time_seconds) AS r_all
FROM runs;

-- outdoor(+track) ranks
DROP TABLE IF EXISTS temp.rank_outdoor;
CREATE TEMP TABLE rank_outdoor AS
SELECT run_no,
       RANK() OVER (PARTITION BY distance_km ORDER BY time_seconds) AS r_out
FROM runs
WHERE type IN ('outdoor','track');

-- treadmill ranks
DROP TABLE IF EXISTS temp.rank_treadmill;
CREATE TEMP TABLE rank_treadmill AS
SELECT run_no,
       RANK() OVER (PARTITION BY distance_km ORDER BY time_seconds) AS r_tread
FROM runs
WHERE type = 'treadmill';

-- write back to base table
UPDATE runs
SET rank_all = (SELECT r_all FROM rank_all WHERE rank_all.run_no = runs.run_no);

UPDATE runs
SET rank_outdoor = (SELECT r_out FROM rank_outdoor WHERE rank_outdoor.run_no = runs.run_no);

UPDATE runs
SET rank_treadmill = (SELECT r_tread FROM rank_treadmill WHERE rank_treadmill.run_no = runs.run_no);

-- record flag (your rule: rank_all = 1)
UPDATE runs
SET is_record = CASE WHEN rank_all = 1 THEN 1 ELSE 0 END;

UPDATE runs
SET
  year  = CAST(strftime('%Y', date) AS INTEGER),
  month = CAST(strftime('%m', date) AS INTEGER);


DROP TABLE IF EXISTS temp.rank_year;
CREATE TEMP TABLE rank_year AS
SELECT
  run_no,
  RANK() OVER (
    PARTITION BY distance_km, CAST(strftime('%Y', date) AS INTEGER)
    ORDER BY time_seconds
  ) AS r_year
FROM runs;

UPDATE runs
SET rank_year = (SELECT r_year FROM rank_year WHERE rank_year.run_no = runs.run_no);

UPDATE runs
SET speed_kmh = CASE
  WHEN distance_km > 0 AND time_seconds > 0
  THEN distance_km * 3600.0 / time_seconds
  ELSE NULL
END;

-- Промежуточная temp-таблица для корректного округления пейса
DROP TABLE IF EXISTS temp.pace;
CREATE TEMP TABLE pace AS
SELECT
  run_no,
  CAST(ROUND(time_seconds * 1.0 / distance_km) AS INTEGER) AS spk -- seconds per km (округлён до секунды)
FROM runs
WHERE distance_km > 0;

UPDATE runs
SET
  pace_sec_per_km = (SELECT spk FROM pace WHERE pace.run_no = runs.run_no),
  pace_min_per_km = (SELECT printf('%02d:%02d', spk/60, spk%60) FROM pace WHERE pace.run_no = runs.run_no);


COMMIT;
