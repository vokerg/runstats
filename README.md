# RunStats MCP Stack

This project provides a Model Context Protocol (MCP) server for running statistics, integrated with an OpenAI assistant for querying run data.

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

Run the run script for your platform:
- **Windows**: Run `run.ps1` in PowerShell
- **macOS/Linux**: Run `chmod +x run.sh && ./run.sh`

This will start the OpenAI assistant in interactive chat mode, which connects to the MCP server to query your run data.

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