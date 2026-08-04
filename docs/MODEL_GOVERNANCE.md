# Model governance

## Pilot rule

The system is advisory. A planner confirms or overrides every recommendation.

## Required monitoring

Track monthly and by work centre:

- ON_TIME rate
- mean and median recommended extension
- percentage completed much earlier than recommended Eckende
- percentage still late after recommendation
- planner acceptance rate
- override reasons
- performance by strategy
- performance on new work centres
- missing/unknown feature rates
- number of recommendations capped by guardrails

## Retraining triggers

Review or retrain when:

- input distributions change materially
- strategy rules change
- a new work centre or technical area is introduced
- acceptance rate declines
- ON_TIME improvement disappears
- model files are more than the approved age
- a data-quality audit finds incorrect completion dates

## Model limitations

The strategy model imitates historical SAP assignments. It does not optimise
asset reliability without outcome data.

The Eckende model can improve reported punctuality only when completion dates
represent genuine operational completion. Inflating deadlines without changing
process performance must be detected through padding metrics.
