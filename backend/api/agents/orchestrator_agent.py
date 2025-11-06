from typing import Any, Dict, List, Union
import json
import os
import re

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import AzureChatOpenAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from backend.core.logging import get_logger

logger = get_logger(__name__)
# ------------------------------------------------------------------------------
# Logging (standard library; no structured kwargs)
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Env helpers
# ------------------------------------------------------------------------------
def _get_env(name: str, *, required: bool = True, default: str = "") -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# ------------------------------------------------------------------------------
# Azure Search (READS should use the QUERY key, not the admin key)
# ------------------------------------------------------------------------------
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_INDEX = os.getenv(
    "AZURE_SEARCH_INDEX_NAME", "bc-water-index"
)  # single source of truth across repo
SEARCH_QUERY_KEY = os.getenv("AZURE_SEARCH_KEY")

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_QUERY_KEY),
)


# ------------------------------------------------------------------------------
# Azure Blob Storage (validate pieces; ensure container exists)
# ------------------------------------------------------------------------------
STORAGE_ACCOUNT = _get_env("AZURE_STORAGE_ACCOUNT_NAME")
STORAGE_KEY = _get_env("AZURE_STORAGE_ACCOUNT_KEY")

AZURE_STORAGE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=https;"
    f"AccountName={STORAGE_ACCOUNT};"
    f"AccountKey={STORAGE_KEY};"
    "EndpointSuffix=core.windows.net"
)

blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)


def ensure_container(name: str) -> None:
    container = blob_service_client.get_container_client(name)
    try:
        container.create_container()
    except ResourceExistsError:
        pass


ensure_container("results")


# ------------------------------------------------------------------------------
# Azure OpenAI (unified with sub-agents)
# ------------------------------------------------------------------------------
llm = AzureChatOpenAI(
    azure_endpoint=_get_env("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    or _get_env("AZURE_OPENAI_DEPLOYMENT"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)


# ------------------------------------------------------------------------------
# Optional mapping doc (left here but NOT used to mutate dict keys)
# ------------------------------------------------------------------------------
MAPPING_DOC = {
    "ApplicantInformation": [
        {
            "formFieldLabel": "",
            "domElementId": "V1IsEligibleForFeeExemption",
            "businessTerm": "",
            "type": "radio",
            "required": "true",
            "description": "Government and First Nation Fee Exemption Request for Water Licenses.",
        },
        {
            "formFieldLabel": "",
            "domElementId": "V1IsExistingExemptClient",
            "businessTerm": "",
            "type": "radio",
            "required": "true",
            "description": "Are you an existing exempt client?",
        },
        {
            "formFieldLabel": "",
            "domElementId": "V1FeeExemptionClientNumber",
            "businessTerm": "",
            "type": "text",
            "required": "true",
            "description": "Please enter your client number",
        },
        {
            "formFieldLabel": "",
            "domElementId": "V1FeeExemptionCategory",
            "businessTerm": "",
            "type": "select-one",
            "required": "true",
            "description": "Fee Exemption Category:",
        },
        {
            "formFieldLabel": "",
            "domElementId": "V1FeeExemptionSupportingInfo",
            "businessTerm": "",
            "type": "textarea",
            "required": "true",
            "description": "Please enter any supporting information that will assist in determining your eligibility for a fee exemption. Please refer to help for details on fee exemption criteria and requirements.",
        },
    ]
}


# ------------------------------------------------------------------------------
# Search helper
# ------------------------------------------------------------------------------
def _search_top_contents(query: str, top: int = 3) -> List[str]:
    results = search_client.search(search_text=query, top=top)
    out: List[str] = []
    for r in results:
        # your index should have a 'content' field; adjust if different
        content = r.get("content")
        if content:
            out.append(content)
    return out


# ------------------------------------------------------------------------------
# Sub-agent shims (tool-safe: single string input -> JSON string output)
# ------------------------------------------------------------------------------
def source_agent(query: str, *_args, **_kwargs) -> str:
    docs = _search_top_contents(query, top=3)
    payload = {
        "agent": "SourceAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No relevant data found for source query.",
    }
    return json.dumps(payload)


def usage_agent(query: str, *_args, **_kwargs) -> str:
    docs = _search_top_contents(query, top=3)
    payload = {
        "agent": "UsageAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No relevant data found for usage query.",
    }
    return json.dumps(payload)


def permissions_agent(query: str, *_args, **_kwargs) -> str:
    # Removed naive "+BC Water Sustainability Act" suffix; rely on index semantics
    docs = _search_top_contents(query, top=3)
    payload = {
        "agent": "PermissionsAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No compliance data found.",
    }
    return json.dumps(payload)


# ------------------------------------------------------------------------------
# Storage result
# ------------------------------------------------------------------------------
def store_result(blob_name: str, data: Union[Dict[str, Any], List[Any], str]) -> None:
    ensure_container("results")
    blob_client = blob_service_client.get_blob_client(
        container="results", blob=blob_name
    )
    if not isinstance(data, str):
        data = json.dumps(data)
    blob_client.upload_blob(data, overwrite=True)


# ------------------------------------------------------------------------------
# Input parsing (dict OR JSON string; never mutate keys to lists)
# ------------------------------------------------------------------------------
def parse_json(json_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    try:
        if isinstance(json_data, str):
            size = len(json_data.encode("utf-8"))
            if size > 1_000_000:
                logger.error("JSON input too large: %s bytes", size)
                return {"error": "JSON input too large"}
            parsed = json.loads(json_data)
        else:
            parsed = json_data

        if not isinstance(parsed, dict):
            logger.error("JSON root must be an object, got %s", type(parsed).__name__)
            return {"error": "Invalid JSON format"}

        # Return as-is; higher layers can translate to DOM ids using MAPPING_DOC if needed
        return parsed

    except json.JSONDecodeError as e:
        logger.exception("Invalid JSON format: %s", e)
        return {"error": "Invalid JSON format"}


# ------------------------------------------------------------------------------
# Routing (explicit map; regex expanded incl. 'licence')
#   Tool entrypoint accepts SINGLE string JSON payload: {"field": "...", "value": "..."}
# ------------------------------------------------------------------------------
ROUTE_FUNCS = {
    "SourceAgent": source_agent,
    "UsageAgent": usage_agent,
    "PermissionsAgent": permissions_agent,
}

ROUTE_PATTERNS = {
    "SourceAgent": re.compile(
        r"(?:water[\s_-]?source|^source$|intake|diversion|river|lake|stream|creek|well|groundwater|aquifer|reservoir)",
        re.I,
    ),
    "UsageAgent": re.compile(
        r"(?:use|usage|purpose|consumption|irrigation|agric|industrial|mining|power|domestic|waterworks|conservation|storage|land\s*improvement|cooling|processing)",
        re.I,
    ),
    "PermissionsAgent": re.compile(
        r"(?:permit|licen[cs]e|authorization|approval|compliance|regulation|condition|WSA|section)",
        re.I,
    ),
}


def route_query(payload_json: str) -> str:
    """
    Tool entrypoint. Expects a JSON string:
      {"field": "water_source", "value": "Fraser River"}
    Returns a JSON string from the chosen sub-agent.
    """
    try:
        payload = json.loads(payload_json)
        field = str(payload.get("field", "")).strip()
        value = str(payload.get("value", "")).strip()
    except Exception:
        return json.dumps(
            {"error": "RouteQuery expects JSON: {'field': str, 'value': str}"}
        )

    field_lower = field.lower()

    chosen = None
    for agent, pattern in ROUTE_PATTERNS.items():
        if pattern.search(field_lower):
            chosen = agent
            break

    if not chosen:
        logger.warning("Unknown field encountered: %s", field)
        return json.dumps(
            {"agent": None, "message": "Unknown field", "field": field, "value": value}
        )

    logger.info("Routing field '%s' to agent '%s'", field, chosen)
    fn = ROUTE_FUNCS[chosen]

    # IMPORTANT: pass the user-provided VALUE (query) to the agent
    result = fn(value)
    return result


# ------------------------------------------------------------------------------
# Process JSON and emit UI-friendly patches for "enter in form"
# ------------------------------------------------------------------------------
def process_json(json_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    logger.info("Processing JSON data")
    mapped_fields = parse_json(json_data)
    if "error" in mapped_fields:
        return mapped_fields

    # simple prompts for missing fields; expand as needed
    prompts = {
        "water_source": "Please specify the water source (e.g., Fraser River, Okanagan Lake).",
        "usage_type": "Please provide the water usage type (e.g., irrigation, industrial).",
        "permit_status": "Please indicate the permit status or requirements.",
    }

    results: Dict[str, Any] = {}
    missing_fields: List[Dict[str, str]] = []
    patches: List[Dict[str, Any]] = []

    for field, value in mapped_fields.items():
        if value in (None, "", []):
            missing_fields.append(
                {
                    "field": field,
                    "prompt": prompts.get(field, f"Please provide {field}."),
                }
            )
            continue

        # Route through tool-safe JSON payload
        route_payload = json.dumps({"field": field, "value": value})
        try:
            routed = json.loads(route_query(route_payload))
        except Exception as e:
            logger.exception("Routing failed for field %s: %s", field, e)
            routed = {"agent": None, "error": str(e)}

        results[field] = routed

        # naive confidence/rationale; you can enrich with LLM judgments later
        has_docs = isinstance(routed, dict) and bool(routed.get("documents"))
        confidence = 0.6 if has_docs else 0.25
        rationale = (
            "Derived from AI Search results for the provided input."
            if has_docs
            else "No strong matches in the index; value retained as provided."
        )

        patches.append(
            {
                "fieldId": field,  # map to DOM id elsewhere if needed
                "value": value,
                "confidence": confidence,
                "rationale": rationale,
                "agent": routed.get("agent") if isinstance(routed, dict) else None,
            }
        )

        # Persist per-field result (best-effort)
        try:
            store_result(f"result_{field}.json", routed)
        except Exception as e:
            logger.exception("Failed to store result for %s: %s", field, e)

    status = "incomplete" if missing_fields else "complete"
    message = (
        "Missing fields require clarification."
        if missing_fields
        else "Form completed successfully!"
    )

    return {
        "status": status,
        "missing_fields": missing_fields,
        "results": results,
        "patches": patches,  # <-- front-end can use this for “enter in form”
        "message": message,
    }


# ------------------------------------------------------------------------------
# Orchestrator Agent (ReAct) with escaped braces in prompt example
# ------------------------------------------------------------------------------
orchestrator_tools = [
    Tool(
        name="RouteQuery",
        func=route_query,  # single string JSON payload
        description=(
            "Routes a field/value payload to the appropriate subagent. "
            'Input must be JSON like: {"field": "water_source", "value": "Fraser River"}'
        ),
    ),
    Tool(
        name="SourceAgent",
        func=source_agent,
        description="Query water source context. Input: a natural-language query string.",
    ),
    Tool(
        name="UsageAgent",
        func=usage_agent,
        description="Query water use/purpose context. Input: a natural-language query string.",
    ),
    Tool(
        name="PermissionsAgent",
        func=permissions_agent,
        description="Query permitting/compliance context. Input: a natural-language query string.",
    ),
]

prompt_template = PromptTemplate.from_template("""
You are an Orchestrator for a BC Water Licence form assistant.
Guidelines:
- Prefer calling **RouteQuery** once per field/value. Do **not** call multiple tools for the same field.
- Do not exceed **3 tool calls** total. If uncertain after 1-2 calls, ask **one** clarifying question and then stop.
- When you have enough information, produce **Final Answer** immediately in the requested JSON format.

Goal:
- Analyze the enriched JSON input and determine missing required fields by section.
- Route to agents in order: Source (foundational), then Usage, then Permissions when needed.
- If dependencies exist (e.g., source affects purpose), sequence tool calls accordingly.
- Ask clear clarifying questions when information is missing.
- When complete, aggregate results and propose final values.

Available tools:
{tools}

You can call one of these tools by name: {tool_names}

Use the following ReAct format:

Question: {input}
Thought: reflect on what to do next
Action: one of [{tool_names}]
Action Input: the input for the selected tool
Observation: the result of the tool
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information to respond
Final Answer: a concise JSON object of the form
{{
  "routes": ["SourceAgent: ..., UsageAgent: ..."],
  "clarifications": ["..."],
  "finalValues": {{"fieldId": "value"}}  # include only when all required fields are filled
}}

Begin!
{agent_scratchpad}
""")

orchestrator = create_react_agent(
    llm=llm, tools=orchestrator_tools, prompt=prompt_template
)
orchestrator_executor = AgentExecutor(
    agent=orchestrator,
    tools=orchestrator_tools,
    handle_parsing_errors=True,
    max_iterations=10,
    early_stopping_method="force",
)
