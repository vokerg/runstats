# run_complete.ps1 - Complete setup and run script for Windows
# This script initializes the environment, data, and runs the assistant v2
# Usage: .\run_complete.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Runs Database Assistant - Complete Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check and create virtual environment
Write-Host "📦 Checking Python environment..." -ForegroundColor Green
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    Write-Host "✅ Virtual environment created"
}

# Step 2: Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Green
& .venv\Scripts\Activate.ps1
Write-Host "✅ Virtual environment activated"

# Step 3: Install dependencies
Write-Host "📥 Installing dependencies..." -ForegroundColor Green
if (Test-Path "requirements.txt") {
    pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install requirements"
        exit 1
    }
    Write-Host "✅ Dependencies installed"
}

# Step 4: Initialize database if needed
Write-Host "💾 Setting up database..." -ForegroundColor Green
if (-not (Test-Path "db/runs.sqlite")) {
    Write-Host "Creating database schema..."
    sqlite3 db/runs.sqlite < db/tables.sql
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create database schema"
        exit 1
    }
    Write-Host "✅ Database schema created"
} else {
    Write-Host "✅ Database already exists"
}

# Step 5: Load data if needed
if ((Test-Path "resources/run_5k.tsv") -and (Test-Path "db/runs.sqlite")) {
    Write-Host "📊 Loading/updating run data..." -ForegroundColor Green
    python load_5k.py
    python load_10k.py
    Write-Host "✅ Run data loaded"
}

# Step 6: Recompute rankings
Write-Host "🏆 Recomputing rankings..." -ForegroundColor Green
python recompute_ranks.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to recompute ranks"
    exit 1
}
Write-Host "✅ Rankings computed"

# Step 7: Verify .env exists
Write-Host "🔑 Checking environment configuration..." -ForegroundColor Green
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Created .env from .env.example"
        Write-Host "   Please add your OPENAI_API_KEY to .env"
    } else {
        Write-Host "⚠️  No .env file found"
        Write-Host "   Please create .env with: OPENAI_API_KEY=your_key_here"
    }
}

# Step 8: Check for OPENAI_API_KEY
$apiKey = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY")
if (!$apiKey) {
    $apiKey = (Select-String "OPENAI_API_KEY" .env -ErrorAction SilentlyContinue | Select-Object -First 1 | % {$_.Line -replace '.*=\s*',''}).Trim('"', "'")
}

if (!$apiKey -or $apiKey -eq "your_api_key_here") {
    Write-Host "❌ OPENAI_API_KEY not configured" -ForegroundColor Red
    Write-Host "   Set OPENAI_API_KEY in .env or environment variables"
    exit 1
}
Write-Host "✅ OpenAI API key configured"

# Step 9: Start the assistant
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Starting Runs Assistant v2" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Example questions:" -ForegroundColor Cyan
Write-Host "   - What was my fastest 5k outdoor run in 2023?"
Write-Host "   - Show my top 3 10k times overall"
Write-Host "   - How many personal records did I set last year?"
Write-Host "   - What is my fastest track run at 10km?"
Write-Host ""

python openai_runs_assistant_v2.py --chat
