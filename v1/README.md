# Runs Assistant V1

This folder contains the original v1 version of the runs assistant and MCP server.

## Files

- `openai_runs_assistant.py` - Original OpenAI assistant (uses `get_runs` tool)
- `runs_mcp_server.py` - Original MCP server
- `run.ps1` - Run script for Windows (v1)
- `run.sh` - Run script for macOS/Linux (v1)

## Running V1

To run the v1 version instead of v2:

**Windows:**
```powershell
cd v1
.\run.ps1
```

**macOS/Linux:**
```bash
cd v1
chmod +x run.sh
./run.sh
```

## Status

These files are no longer actively maintained. Use the v2 versions in the root directory for new work.

- `openai_runs_assistant_v2.py` - Enhanced assistant with better query capabilities
- `runs_mcp_server_v2.py` - Enhanced MCP server with rank filtering and year support
- `run_v2.ps1` / `run_v2.sh` - V2 run scripts

## Migration Notes

The v2 versions include:
- Support for `rank_outdoor_track`, `rank_track`, `rank_treadmill` columns
- Year-based filtering
- Better parameter validation for LLM usage
- Enhanced tool descriptions
