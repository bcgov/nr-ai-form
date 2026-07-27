POSSE Checker

This is a two part package where, to check if the POSSE's html aligns with our current version of form defintions.

Architecture:

The `Form Compare.js` will load the json for the POSSE step and provide a comparison report on the matched, renamed and mismatched sections.

The comparison happens on the browser and the report is published to the browser console.


1. Python Server

In order to execute, you need the python server running. It contains one GET endpoint which will furnish the contents of a json file identified by the step number.

Update `JSON_FOLDER` to your specific folder - e.g., `"C:\\Users\\abc\\nr-ai-form\\agentic_ai_backend\\agents\\formsupportagent\\formdefinitions"`

To run the python server, execute these commands

To build:
```
pip install fastapi uvicorn
```

To run:
```
uvicorn server:app --reload
```

2. Form Compare.js

On the specific POSSE step you want to test, go to your browser's developer tools and add a JS Snippet and paste the contents of this file.

On Chrome, you can execute the snippet by `Ctrl + Enter` and observe the output on the console. The output of the console will guide you on the outcome and possible actions to take.