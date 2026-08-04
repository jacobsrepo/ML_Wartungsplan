$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment and installing dependencies..."
uv sync --extra dev

Write-Host ""
Write-Host "Environment created."
Write-Host "Next:"
Write-Host "1. Confirm data\raw\SAP_notintime_.xlsx exists."
Write-Host "2. Run: uv run python scripts\00_check_environment.py"
Write-Host "3. Run: uv run python scripts\01_build_datasets.py"
