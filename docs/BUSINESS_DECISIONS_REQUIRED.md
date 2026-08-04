# Business decisions required before the pilot

Complete this document with maintenance planning.

## KPI definition

- Which completion date is authoritative: `IDAT2`, `IDAT3`, `GETRI`, or another?
- Is ON_TIME defined as `Abschlussdatum <= Eckende`?
- Are weekends and Thuringian public holidays excluded?
- Which SAP factory calendars differ from the standard Thuringia calendar?

## Service level

- Target ON_TIME rate:
- Default quantile: Q80 / Q85 / Q90
- Maximum acceptable unnecessary padding:

## Deadline guardrails

- Absolute maximum extension in working days:
- Maximum extension as a fraction of cycle:
- Different limits for weekly/monthly/yearly strategies:
- Minimum historical examples before accepting an ML recommendation:

## Strategy rules

- Exact business difference between `8160_W` and `UBK_W1`:
- Exact business difference between `8160_M` and `UBK_M1`:
- Which fields contain this distinction?
- Which strategy assignments in SAP are known to be outdated?

## Email and approval

- Who receives plan recommendations?
- Who receives Eckende recommendations?
- Who may override?
- Mandatory override reasons:
- Escalation after no response:

## Deployment

- Approved API host:
- Authentication method:
- Data retention:
- Logging location:
- Model owner:
- Process owner:
