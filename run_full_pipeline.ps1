$ErrorActionPreference = "Stop"

uv run python scripts\00_check_environment.py
uv run python scripts\01_build_datasets.py
uv run python scripts\02_train_strategy.py
uv run python scripts\03_train_deadline.py
uv run pytest

Write-Host ""
Write-Host "Training complete."
Write-Host "Start the API with:"
Write-Host "uv run python scripts\07_run_api.py"
