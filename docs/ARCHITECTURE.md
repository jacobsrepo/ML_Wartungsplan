# System architecture

```text
                         BEFORE PLAN ENTRY
Requester / planner enters:
work centre, technical location, equipment, task description
                                  |
                                  v
                   Strategy recommendation model
                  MPLA.STRAT + probability + alternatives
                                  |
                                  v
                       Planner email / approval
                                  |
                                  v
                     Maintenance plan entered in SAP
                                  |
                                  v
                    SAP scheduling generates order
                 Abrufdatum, Plandatum, Eckstart, Auftrag
                                  |
                                  v
                       Eckende quantile models
                    Q50 / Q80 / Q85 / Q90 completion
                                  |
                                  v
                  Guardrail and business-rule engine
             smallest realistic deadline without excess padding
                                  |
                                  v
                       Planner email / approval
                                  |
                                  v
                     Order execution and completion
                                  |
                                  v
                         Feedback and monitoring
             actual completion, ON_TIME, overrides, reasons
```

## Components

### Data builders

- `build_strategy_dataset.py` uses `Wartungsplan- Snapshot`
- `build_deadline_dataset.py` uses `Abfrage1`

### Models

- Strategy: TF-IDF + categorical encoding + balanced logistic regression
- Eckende: text compression + categorical/numeric features +
  histogram gradient-boosting quantile regression

### Inference

- `RecommendationService` loads saved model files
- applies feature engineering consistently
- applies deadline caps and minimum-history checks
- returns review status and alternatives

### Delivery

- FastAPI returns JSON and rendered HTML
- Power Automate sends the email and logs the decision
- SAP write-back remains disabled during the pilot
