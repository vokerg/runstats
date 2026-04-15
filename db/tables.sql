CREATE TABLE IF NOT EXISTS runs (
  run_no          INTEGER PRIMARY KEY,
  date            TEXT NOT NULL,                         -- YYYY-MM-DD
  distance_km     REAL NOT NULL,
  time_seconds    INTEGER NOT NULL,
  type            TEXT NOT NULL CHECK (type IN ('outdoor','track','treadmill')),
  rank_all        INTEGER,
  rank_outdoor    INTEGER,
  rank_outdoor_track INTEGER,
  rank_track      INTEGER,
  rank_treadmill  INTEGER,
  is_record       INTEGER CHECK (is_record IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_runs_dist_time ON runs(distance_km, time_seconds);
CREATE INDEX IF NOT EXISTS idx_runs_type_dist ON runs(type, distance_km);



ALTER TABLE runs ADD COLUMN year INTEGER;
ALTER TABLE runs ADD COLUMN month INTEGER;
ALTER TABLE runs ADD COLUMN rank_year INTEGER;

ALTER TABLE runs ADD COLUMN speed_kmh REAL;
ALTER TABLE runs ADD COLUMN pace_sec_per_km INTEGER;
ALTER TABLE runs ADD COLUMN pace_min_per_km TEXT;