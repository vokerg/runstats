# Database

This folder contains the SQLite database and schema files for the runs application.

## Files

- `runs.sqlite` - Main database file containing all run records with rankings
- `tables.sql` - Database schema definition
- `recompute_ranks.sql` - SQL script to recompute all ranking columns

## Initialization

To create a fresh database:
```bash
sqlite3 runs.sqlite < tables.sql
```

To load run data:
```bash
python load_5k.py
python load_10k.py
```

To recompute rankings:
```bash
python recompute_ranks.py
```
