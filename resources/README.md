# Resources

This folder contains data files and other resources for the runs application.

## Files

- `run_5k.tsv` - Tab-separated run data for 5km distance
  - Columns: time (HH:MM:SS), date (DD.MM.YYYY), type (t/s/empty), run_no
  - t = treadmill, s = track/stadium, empty = outdoor

- `run_10k.tsv` - Tab-separated run data for 10km distance
  - Format same as run_5k.tsv

## Format Reference

Each TSV file has 4 tab-separated columns:
1. **Time**: HH:MM:SS or MM.SS format
2. **Date**: DD.MM.YYYY format
3. **Type**: 
   - `t` = treadmill
   - `s` = track/stadium
   - empty = outdoor
4. **Run Number**: Sequential numeric ID
