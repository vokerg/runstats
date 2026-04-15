#!/bin/bash
# run_v2.sh - Run script for macOS/Linux with MCP server v2
# Launches the runs assistant with the new MCP server and enhanced query capabilities

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ .venv directory not found. Run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Run the OpenAI assistant v2 in chat mode
echo "🚀 Starting Runs Assistant v2..."
echo "Using MCP server runs_mcp_server_v2.py with enhanced query capabilities"

python3 openai_runs_assistant_v2.py --chat
