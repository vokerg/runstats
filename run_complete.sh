#!/bin/bash
# run_complete.sh - Complete setup and run script for macOS/Linux
# This script initializes the environment, data, and runs the assistant v2
# Usage: ./run_complete.sh

set -e  # Exit on any error

echo "========================================"
echo "Runs Database Assistant - Complete Setup"
echo "========================================"
echo ""

# Step 1: Check and create virtual environment
echo "📦 Checking Python environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Step 2: Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"

# Step 3: Install dependencies
echo "📥 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Step 4: Initialize database if needed
echo "💾 Setting up database..."
if [ ! -f "runs.sqlite" ]; then
    echo "Creating database schema..."
    sqlite3 runs.sqlite < tables.sql
    echo "✅ Database schema created"
else
    echo "✅ Database already exists"
fi

# Step 5: Load data if needed
if [ -f "run_5k.tsv" ] && [ -f "runs.sqlite" ]; then
    echo "📊 Loading/updating run data..."
    python3 load_5k.py
    python3 load_10k.py
    echo "✅ Run data loaded"
fi

# Step 6: Recompute rankings
echo "🏆 Recomputing rankings..."
python3 recompute_ranks.py
echo "✅ Rankings computed"

# Step 7: Verify .env exists
echo "🔑 Checking environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  Created .env from .env.example"
        echo "   Please add your OPENAI_API_KEY to .env"
    else
        echo "⚠️  No .env file found"
        echo "   Please create .env with: OPENAI_API_KEY=your_key_here"
    fi
fi

# Step 8: Check for OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    OPENAI_API_KEY=$(grep "OPENAI_API_KEY" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "'"'"'')
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_api_key_here" ]; then
    echo "❌ OPENAI_API_KEY not configured"
    echo "   Set OPENAI_API_KEY in .env or environment variables"
    exit 1
fi
echo "✅ OpenAI API key configured"

# Step 9: Start the assistant
echo ""
echo "========================================"
echo "Starting Runs Assistant v2"
echo "========================================"
echo ""
echo "📝 Example questions:"
echo "   - What was my fastest 5k outdoor run in 2023?"
echo "   - Show my top 3 10k times overall"
echo "   - How many personal records did I set last year?"
echo "   - What is my fastest track run at 10km?"
echo ""

python3 openai_runs_assistant_v2.py --chat
