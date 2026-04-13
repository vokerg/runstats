# Setup script for Windows

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Setup database
python -c "
import sqlite3
con = sqlite3.connect('runs.sqlite')
with open('tables.sql', 'r') as f:
    con.executescript(f.read())
con.close()
print('Database setup complete')
"

# Load data
python load_5k.py
python load_10k.py

# Recompute ranks
python recompute_ranks.py

Write-Host "Setup complete. Copy .env.example to .env and add your OPENAI_API_KEY"