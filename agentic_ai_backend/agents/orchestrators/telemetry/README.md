# Telemetry

This directory contains:

* `telemetry_interface.py` - a prescribed contract by which telemetry implementations must conform
    * includes methods for capturing `request`, `exception`, `metric`, `event` and `dependency`     
* a telemetry implementation using `azure-monitor-opentelemetry` distro. All telemetry is captured as span events to message telemetry.(see: [Microsoft Azure documentation](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview?tabs=webapps))
* a middleware function invoked in the orchestartor `POST /invoke` endpoint. Currently this captures: `request` and `exceptions`.

## Monitoring telemetry:

For this basic Azure Monitor set-up we can go into the Azure portal > Application Insights to view:
(note use the attached telemetry queries)

* `requests`: HTTP requests to the Form Assist API /invoke endpoint. 
* `AI Mesages`: Chat dialog - User query and aggregated Assistant response
* Form Support and Conversation agent responses
* `Exceptions`: stack trace for errors thrown from orchestartor 

<details>
<summary>Tips for navigating Application Insightsin the Azure Portal</summary>

* To view telemetry go to the 'Application Insights' service > Monitoring > Logs
* Telemetry is found under `requests` and `exceptions` tables.
* This is a saved KQL query to view AI Messages:

```kql
requests
| extend d = column_ifexists("customDimensions", dynamic(null))
| extend rawPayload = coalesce(tostring(d["Properties.invoke.payload"]), tostring(d["invoke.payload"]))
| where operation_Name == "POST /invoke" and isnotempty(rawPayload)
| extend payload = parse_json(rawPayload)
| extend user = case(
    isnotempty(tostring(payload[0]["query"])), tostring(payload[0]["query"]),
    isnotempty(tostring(payload[0]["request"])), tostring(payload[0]["request"]),
    isnotempty(tostring(payload[0]["user"])), tostring(payload[0]["user"]),
    ""
  )
| extend ai = case(
    isnotempty(tostring(payload[1]["response"]["response"])), tostring(payload[1]["response"]["response"]),
    isnotempty(tostring(payload[1]["response"])), tostring(payload[1]["response"]),
    isnotempty(tostring(payload[1]["ai"])), tostring(payload[1]["ai"]),
    ""
  )
| extend step_number = tostring(payload[0]["step_number"])
| extend session_id = tostring(payload[0]["session_id"])
| extend user = replace_regex(user, @"[\r\n]+", " ")
| extend ai = replace_regex(ai, @"[\r\n]+", " ")
| project timestamp, name, operation_Name, resultCode, success, session_id, step_number, user, ai
| order by timestamp desc
```

* use the 'Observability Agent' copilot if required
<details>



