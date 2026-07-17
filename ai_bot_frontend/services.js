import { FormSteps } from "./stepmappers.js";
const ORCHESTRATOR_API_URL = "http://localhost:8002/invoke";

async function invokeOrchestrator(query, step_number, session_id = null) {
  const payload = {
    query: query,
    step_number: step_number,
    session_id: session_id
  };

  try {
    const response = await fetch(ORCHESTRATOR_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Orchestrator API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error invoking Orchestrator Agent:", error);
    throw error;
  }
}

export { invokeOrchestrator };
