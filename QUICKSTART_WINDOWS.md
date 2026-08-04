# Five-command Windows quick start

Open PowerShell inside `ML_Wartungsplan`.

```powershell
uv sync --extra dev
uv run python scripts\00_check_environment.py
uv run python scripts\01_build_datasets.py
uv run python scripts\02_train_strategy.py
uv run python scripts\03_train_deadline.py
```

Then start the API:

```powershell
uv run python scripts\07_run_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

The first Excel processing and deadline training may take several minutes
because the workbook contains tens of thousands of rows.
