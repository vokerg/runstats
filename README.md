# RunStats MCP Stack

This project provides a Model Context Protocol (MCP) server for running statistics, integrated with an OpenAI assistant for querying run data.

## Project Structure

```
runstats/
├── db/                           # Database files and schemas
│   ├── runs.sqlite              # SQLite database (generated)
│   ├── tables.sql               # Database schema
│   └── recompute_ranks.sql      # Ranking computation script
├── resources/                    # Data files and resources
│   ├── run_5k.tsv               # 5km run data
│   └── run_10k.tsv              # 10km run data
├── logs/                         # Application logs (generated)
│   └── runstats.log             # Application log file
├── v1/                           # Original v1 implementation (archived)
│   ├── openai_runs_assistant.py
│   └── runs_mcp_server.py
├── openai_runs_assistant_v2.py   # Main assistant (v2)
├── runs_mcp_server_v2.py         # Main MCP server (v2)
├── load_5k.py                    # Load 5km data into database
├── load_10k.py                   # Load 10km data into database
├── recompute_ranks.py            # Recompute ranking columns
├── run_v2.ps1 / run_v2.sh        # Quick start scripts (v2)
└── run_complete.ps1 / run_complete.sh  # Full setup and run scripts
```

## Setup

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. Clone or download this repository.

2. Run the setup script for your platform:
   - **Windows**: Run `setup.ps1` in PowerShell
   - **macOS/Linux**: Run `chmod +x setup.sh && ./setup.sh`

3. Copy `.env.example` to `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Running the Stack

### Quick Start (Recommended)

Use the complete setup and run script:
- **Windows**: Run `.\run_complete.ps1` in PowerShell
- **macOS/Linux**: Run `chmod +x run_complete.sh && ./run_complete.sh`

This will:
- Create virtual environment
- Install dependencies
- Initialize database
- Load run data
- Recompute rankings
- Start the interactive assistant

### Quick Start (If Already Setup)

Use the quick start script:
- **Windows**: Run `.\run_v2.ps1` in PowerShell
- **macOS/Linux**: Run `chmod +x run_v2.sh && ./run_v2.sh`

## Features

### Query Capabilities (v2)

Ask natural language questions about your runs:
- "What was my fastest 5k outdoor run in 2023?"
- "Show my top 3 10k times overall"
- "How many personal records did I set last year?"
- "What is my fastest track run at 10km?"

### Ranking Types

The database tracks multiple ranking systems:
- `rank_all` - Fastest time overall (all surfaces)
- `rank_outdoor_track` - Fastest among outdoor and track runs (excluding treadmill)
- `rank_track` - Fastest among track runs only
- `rank_treadmill` - Fastest among treadmill runs only
- `is_record` - Personal record (rank_all = 1)

### Run Types

- **outdoor** - Outdoor running
- **track** - Track/stadium running (marked with 's' in data)
- **treadmill** - Treadmill running (marked with 't' in data)

## Data Format

Run data files (resources/*.tsv) use tab-separated format:
```
HH:MM:SS    DD.MM.YYYY    type    run_number
```

Example:
```
0:30:15	01.05.2017	t	1
0:27:35	05.05.2017	t	2
0:23:49	03.03.2022		586
```

- **Time**: Hours:Minutes:Seconds
- **Date**: Day.Month.Year
- **Type**: `t` (treadmill), `s` (track), or empty (outdoor)
- **Run Number**: Unique sequential ID

## Advanced Usage

### Manual Database Operations

```bash
# Load 5km runs
python load_5k.py

# Load 10km runs
python load_10k.py

# Recompute all rankings
python recompute_ranks.py
```

### Access Database Directly

```bash
sqlite3 db/runs.sqlite
```

### Using Previous Version (v1)

The original v1 implementation is archived in the `v1/` folder.
To use v1 instead:
```bash
python v1/openai_runs_assistant.py --chat
```

## Components

- **SQLite Database**: Stores run records in `runs.sqlite`
- **MCP Server**: `runs_mcp_server.py` - Provides tools for querying and updating run data
- **OpenAI Assistant**: `openai_runs_assistant.py` - Natural language interface to run data

## Data Loading

The setup script loads sample data from `run_5k.tsv` and `run_10k.tsv` for 5K and 10K runs.

To load additional data, run the load scripts manually:
- `python load_5k.py`
- `python load_10k.py`

Then recompute ranks:
- `python recompute_ranks.py`