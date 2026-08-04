# Power Automate implementation

## Important connectivity point

A cloud Power Automate flow cannot call `http://localhost:8000` on your laptop
directly. For the pilot, use one of these approved company options:

- deploy the API to an internal Azure/Databricks service
- expose the local/internal API through an approved on-premises data gateway
- use Power Automate Desktop on the same machine/network

Coordinate the final hosting method with Bosch IT/security.

---

## Flow A — maintenance-plan recommendation email

### Trigger

Use one:

- Power Apps form submission
- Dataverse/SharePoint item created
- manual test trigger during development

### Required inputs

```text
responsible_work_center
technical_location
task_description
equipment_id
equipment_text
requester_email
```

### HTTP action

Method:

```text
POST
```

Endpoint:

```text
https://<approved-host>/recommend/strategy
```

Headers:

```text
Content-Type: application/json
x-api-key: <secret stored in a secure connection/environment variable>
```

Body:

```json
{
  "responsible_work_center": "@{triggerBody()?['work_center']}",
  "technical_location": "@{triggerBody()?['technical_location']}",
  "task_description": "@{triggerBody()?['task_description']}",
  "equipment_id": "@{triggerBody()?['equipment_id']}",
  "equipment_text": "@{triggerBody()?['equipment_text']}"
}
```

### Parse JSON

Use the HTTP response. The main values are:

```text
body.recommendation.predicted_strategy
body.recommendation.prediction_confidence
body.recommendation.top_2_strategy
body.recommendation.top_2_probability
body.recommendation.review_status
body.email_html
```

### Send email

Use **Send an email (V2)**.

- To: requester or mapped planner
- Subject: `[RECOMMENDATION] Maintenance plan - <technical location>`
- Body: `body.email_html`
- Is HTML: Yes

### Log the decision

Store:

```text
request_id
timestamp
requester
model_version
input fields
recommended strategy
confidence
accepted strategy
accepted / overridden / rejected
override reason
```

---

## Flow B — Eckende recommendation email

### Trigger

Use a daily SAP order extract, Dataverse row or an event after the maintenance
order has been generated.

### Required inputs

```text
order_number
responsible_work_center
technical_location
task_description
strategy
planned_date
call_date
current_eckende
cycle_days
opening_horizon_days
factory_calendar
call_confirm
planner_email
```

### HTTP action

Endpoint:

```text
POST https://<approved-host>/recommend/eckende
```

The response contains:

```text
recommended_eckende
recommended_extension_workdays
selected_service_level
quantile_extensions
similar_history_count
guardrail_applied
manual_review_reasons
review_status
email_html
```

### Approval

Use **Start and wait for an approval** with choices:

```text
Accept recommendation
Use different Eckende
Reject recommendation
```

Do not automatically update SAP during the initial pilot.

### Feedback table

Store:

```text
order number
current Eckende
recommended Eckende
accepted Eckende
Q50/Q80/Q85/Q90
planner decision
override reason
actual completion date
final ON_TIME result
model version
```

This table becomes the future retraining and governance source.
