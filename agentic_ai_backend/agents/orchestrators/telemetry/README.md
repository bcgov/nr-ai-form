# Telemetry

This directory contains:

* `telemetry_interface.py` - a prescribed contract by which telemetry implementations must conform
    * includes methods for capturing `request`, `exception`, `metric`, `event` and `dependency`
* a telemetry implementation using the `azure-monitor-opentelemetry` distro. All telemetry is captured as span events to message telemetry. See: [Microsoft Azure documentation](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview?tabs=webapps)

## Monitoring telemetry

For this basic Azure Monitor setup, use the Azure portal > Application Insights to view telemetry in the `requests`, `exceptions`, and related trace tables.

* `AI Messages`: chat dialog, user query, and aggregated assistant response when emitted by agent workflow components
* Form Support and Conversation agent responses
* `Exceptions`: stack trace for errors thrown from orchestrator components

<details>
<summary>Tips for navigating Application Insights in the Azure Portal</summary>

* To view telemetry, go to the Application Insights service > Monitoring > Logs.
* Telemetry is found under `requests`, `exceptions`, traces, and custom event tables depending on the emitter.
* Use the Observability Agent copilot if required.

</details>