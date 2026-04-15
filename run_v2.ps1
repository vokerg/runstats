# run_v2.ps1 - Run script for Windows with MCP server v2
# Launches the runs assistant with the new MCP server and enhanced query capabilities

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error ".venv directory not found. Run setup.ps1 first."
    exit 1
}

# Activate virtual environment
& .venv\Scripts\Activate.ps1

# Run the OpenAI assistant v2 in chat mode
Write-Host "🚀 Starting Runs Assistant v2..." -ForegroundColor Green
Write-Host "Using MCP server runs_mcp_server_v2.py with enhanced query capabilities" -ForegroundColor Cyan

python openai_runs_assistant_v2.py --chat
