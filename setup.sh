#!/bin/bash

# Setup script for macOS/Linux

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python3 -c "
import sqlite3
import os
con = sqlite3.connect('runs.sqlite')
with open('tables.sql', 'r') as f:
    con.executescript(f.read())
con.close()
print('Database setup complete')
"

# Load data
python3 load_5k.py
python3 load_10k.py

# Recompute ranks
python3 recompute_ranks.py

echo "Setup complete. Copy .env.example to .env and add your OPENAI_API_KEY"