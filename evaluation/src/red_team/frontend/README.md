# Browser UI for Red Team scans

This folder contains the lightweight web interface for running PyRIT evaluations in the browser and inspecting saved JSON results.

## Run it

```bash
cd evaluation
uv run python -m src.red_team.web_app
```

Then open:

- http://localhost:8001

## Features

- Launch scan runs from a browser form
- Use PyRIT attack types and seed datasets
- View saved JSON reports immediately from the dashboard
- Reuse the same report storage folder as the CLI workflow
