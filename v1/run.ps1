# Run script for Windows (V1)
# Run from the v1 directory: cd v1; .\run.ps1

# Activate virtual environment (from parent directory)
& ..\\.venv\Scripts\Activate.ps1

# Run the OpenAI assistant in chat mode
python openai_runs_assistant.py --chat