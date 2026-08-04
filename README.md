# ML_Wartungsplan 🔧📈

A local machine-learning system for two connected SAP maintenance tasks:

1. **Maintenance-strategy recommendation**  
   Predict the historically assigned `MPLA.STRAT` from information available
   before or during maintenance-plan creation.

2. **Realistic Eckende recommendation**  
   Predict several completion-time quantiles and recommend the smallest
   realistic deadline associated with the agreed service level, while applying
   business guardrails so deadlines are not pushed unnecessarily far away.

The system also exposes a FastAPI service and generates HTML email content that
Power Automate can send to the responsible planner.

---

## Current status

The repository already contains the previously trained strategy model and its
processed dataset. That baseline achieved approximately:

- Accuracy: **95.8%**
- Macro-F1: **94.1%**
- Main error: confusion between `8160_W` and `UBK_W1`

The Eckende model must be trained from the original `SAP_notintime_.xlsx`
workbook because it uses completed historical orders.

---

## Repository structure

```text
ML_Wartungsplan/
├── config/                 Model settings and business guardrails
├── data/
│   ├── raw/                Original SAP workbook; excluded from Git
│   ├── processed/          Generated ML datasets
│   ├── reference/          Work-centre → planner email mapping
│   └── sample/             Example API/CSV inputs
├── docs/                   Architecture, SAP lifecycle and automation guide
├── models/                 Saved production pipelines
├── notebooks/              Step-by-step analysis and training
├── reports/                Metrics, predictions and simulation results
├── scripts/                Commands to build, train and predict
├── src/ml_wartungsplan/    Reusable Python package and API
├── templates/              Email templates
└── tests/                  Feature and date tests
```

---

## First-time setup on Windows

Open PowerShell in the repository root.

### 1. Install `uv` when it is not already installed

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell after installation.

### 2. Create the environment

```powershell
uv sync --extra dev
```

Or run:

```powershell
.\setup_windows.ps1
```

### 3. Confirm the source workbook

The file must exist here:

```text
data\raw\SAP_notintime_.xlsx
```

The supplied project package already includes it locally, but `.gitignore`
prevents it from being committed.

### 4. Check the environment

```powershell
uv run python scripts\00_check_environment.py
```

---

## Build the two datasets

```powershell
uv run python scripts\01_build_datasets.py
```

Outputs:

```text
data\processed\maintenance_strategy_ml_dataset.csv
data\processed\maintenance_deadline_ml_dataset.csv
reports\deadline\data_quality.json
```

The deadline data builder:

- keeps completed orders with a valid planned date
- converts SAP/Excel dates
- calculates actual working-day extension after `Plandatum`
- calculates the current ON_TIME result against `Eckende`
- removes clearly invalid date ranges
- marks unusually long targets that were clipped
- creates only features available before completion

---

## Train the strategy model

```powershell
uv run python scripts\02_train_strategy.py
```

Outputs:

```text
models\maintenance_strategy_pipeline.joblib
reports\strategy\metrics.json
reports\strategy\test_predictions.csv
```

---

## Train the Eckende quantile models

```powershell
uv run python scripts\03_train_deadline.py
```

The training uses a **time-based holdout**:

```text
Older completed orders → training
Newest completed orders → unseen test
```

It trains:

```text
Q50  typical deadline
Q80  approximately 80% service level
Q85  default recommendation
Q90  conservative deadline
```

Outputs:

```text
models\deadline_quantile_bundle.joblib
reports\deadline\metrics.json
reports\deadline\test_predictions.csv
```

The report compares:

- current historical ON_TIME rate
- simulated ON_TIME rate using the selected quantile
- current average deadline extension
- recommended average extension
- model coverage and unnecessary padding

---

## Run the entire pipeline

```powershell
.\run_full_pipeline.ps1
```

---

## Try new CSV recommendations

### Strategy

```powershell
uv run python scripts\04_predict_strategy_csv.py
```

Input:

```text
data\sample\strategy_requests.csv
```

Output:

```text
reports\strategy\new_recommendations.csv
```

### Eckende

Run this after training the deadline models:

```powershell
uv run python scripts\05_predict_deadline_csv.py
```

Input:

```text
data\sample\order_requests.csv
```

Output:

```text
reports\deadline\new_recommendations.csv
```

---

## Start the API

```powershell
uv run python scripts\07_run_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Available endpoints:

```text
GET  /health
POST /recommend/strategy
POST /recommend/eckende
POST /recommend/full
```

Example strategy request:

```json
{
  "responsible_work_center": "EH_STPM",
  "technical_location": "8160-330",
  "task_description": "wöchentlicher TPM Wartungsplan HFM6M3",
  "equipment_id": "HFM6M3",
  "equipment_text": "HFM6 Montageanlage"
}
```

Example Eckende request:

```json
{
  "order_number": "7200000001",
  "responsible_work_center": "EH_STPM",
  "technical_location": "8160-330",
  "task_description": "wöchentlicher TPM Wartungsplan HFM6M3",
  "strategy": "8160_W",
  "planned_date": "2026-09-10",
  "call_date": "2026-08-20",
  "current_eckende": "2026-09-10",
  "cycle_days": 7,
  "opening_horizon_days": 14,
  "factory_calendar": "TH",
  "call_confirm": "X"
}
```

---

## Power Automate integration

Read:

```text
docs\POWER_AUTOMATE.md
```

The recommended first pilot is **email and planner approval only**:

```text
Power Apps / SAP extract
        ↓
Power Automate HTTP request
        ↓
FastAPI recommendation
        ↓
Planner email
        ↓
Accept / change / reject
        ↓
Log recommendation and actual result
```

Do not automatically update SAP during the first pilot.

---

## Guardrails requiring business approval

Edit:

```text
config\guardrails.yaml
```

The included values are pilot placeholders:

- absolute maximum extension: 60 working days
- maximum extension: 20% of the maintenance cycle
- minimum similar history: 20 orders
- manual review whenever a cap is applied

The maintenance-planning team must approve these rules before operational use.

---

## Important interpretation

The strategy model predicts:

> Which strategy was historically assigned to a similar maintenance item?

It does not yet prove:

> Which strategy is objectively optimal for reliability, cost and downtime?

The deadline model addresses a different business goal:

> Increase ON_TIME completion while minimising unnecessary deadline extension.

For true maintenance-strategy optimisation, later add failure, downtime, labour,
spare-parts cost, production loss and asset-criticality outcomes.
