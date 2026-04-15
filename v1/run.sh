#!/bin/bash
# Run script for macOS/Linux (V1)
# Run from the v1 directory: cd v1; chmod +x run.sh; ./run.sh

# Activate virtual environment (from parent directory)
source ../.venv/bin/activate

# Run the OpenAI assistant in chat mode
python3 openai_runs_assistant.py --chat