import asyncio
import time
from dataclasses import dataclass
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import os
import sys
from agents.formsupportagent.models.formsupportmodel import FormSupportAgentClientSettings
from utils.tenantsettings import settings_cache_parts, top_level_setting_from_client

load_dotenv()


@dataclass
class _CachedCommonInstructions:
    text: str
    expires_at: float


_COMMON_INSTRUCTIONS_CACHE: dict[tuple[str, str, str], _CachedCommonInstructions] = {}
_COMMON_INSTRUCTIONS_CACHE_TTL_SECONDS = float(os.getenv("FORM_SUPPORT_PROMPT_CACHE_TTL_SECONDS", "300"))


class AzureGatewayChatCompletionClient(OpenAIChatCompletionClient):
    """Compatibility wrapper for gateways that reject null assistant tool-call content."""

    def _prepare_message_for_openai(self, message):
        prepared_messages = super()._prepare_message_for_openai(message)
        for prepared_message in prepared_messages:
            if prepared_message.get("role") == "assistant" and "tool_calls" in prepared_message:
                # Some OpenAI-compatible gateways reject null/empty assistant content when tool_calls are present.
                prepared_message.setdefault("content", " ")
        return prepared_messages


# Backward-compatible alias for older patches/tests that referenced the beta client name.
AzureOpenAIChatClient = AzureGatewayChatCompletionClient

# Add parent directory to path to allow importing 'tools'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def extract_step_from_query(query):
    """
    Extracts the step identifier and actual query from a string like 'step3: query'.
    """
    actual_query = query
    step_identifier = None
    
    if ":" in query:
        parts = query.split(":", 1)
        potential_step = parts[0].strip()
        if potential_step.lower().startswith("step"):
            step_identifier = potential_step
            actual_query = parts[1].strip()
    
    return step_identifier, actual_query

from services.formdefinitionservice import FormDefinitionService
from services.prompttemplateservice import PromptTemplateService
from utils.blobservice import BlobService
from local_mcp.livestock.inprocess_client import (
    LIVESTOCK_WATER_CONSUMPTION_TOOLS,
)
from local_mcp.fishing_licence.inprocess_client import (
    FISHING_LICENCE_TOOLS,
)

def resolve_agent_assets(step_identifier, form_definition_service=None, prompt_template_service=None):
    """
    Resolves form definition JSON and prompt template for a given step identifier.
    Returns (form_definition_dict, prompt_template_str, step_identifier)
    """
    step_key = str(step_identifier)
    if not form_definition_service or not prompt_template_service:
        return None, None, step_key

    json_filename = f"{step_key}.json"
    md_filename = f"{step_key}.md"
    
    form_definition = form_definition_service.fetch_form_definition(json_filename)
    prompt_template = prompt_template_service.fetch_prompt_template(md_filename)

    return form_definition, prompt_template, step_key



class FormSupportAgent():
    def __init__(
        self,
        endpoint,
        api_key,
        deployment_name,
        api_version,
        form_context_str,
        instructions,
        client_settings: FormSupportAgentClientSettings,
    ):
        if not instructions:
            raise ValueError("Instructions (Skill MD) are required to initialize the FormSupportAgent.")

        if isinstance(instructions, str) and os.path.exists(instructions):
            with open(instructions, "r", encoding="utf-8") as handle:
                instructions = handle.read()

        final_instructions = instructions
        
        try:
            # Inject the form context into the template if the placeholder exists
            if "{form_context_str}" in final_instructions :                     
                final_instructions = final_instructions.replace("{form_context_str}", form_context_str)               
            else:
                # If it's a completely custom prompt without the placeholder, 
                # we should probably still append the context so the AI knows the fields
                final_instructions = f"{final_instructions}\n\nHere is the form context:\n{form_context_str}"
                
        except Exception:
            final_instructions = f"{final_instructions}\n\nHere is the form context:\n{form_context_str}"
        

        # Append shared FormSupportAgent rules from tenant blob settings.
        final_instructions += self._load_common_instructions(client_settings)

        client = AzureOpenAIChatClient(
            model=deployment_name,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        agent_kwargs = {
            "instructions": final_instructions,            
            "name": "FormSupportAgent",
        }
        self.agent = client.as_agent(
            **agent_kwargs,
            default_options={"temperature": 0.1},
        )

    def _load_common_instructions(self, client_settings: FormSupportAgentClientSettings) -> str:
        """Load shared FormSupportAgent rules from Azure Blob Storage."""
        connection_string = top_level_setting_from_client(client_settings, "blobConnectionString", required=True)
        container_name = top_level_setting_from_client(client_settings, "containerName", required=True)
        blob_path = top_level_setting_from_client(client_settings, "promptPath", required=True)
        if not connection_string or not container_name or not blob_path:
            raise RuntimeError("FormSupportAgent common instruction blob config is required.")

        client_id, fingerprint = settings_cache_parts(client_settings)
        cache_key = (client_id, fingerprint, blob_path)
        now = time.monotonic()
        cached = _COMMON_INSTRUCTIONS_CACHE.get(cache_key)
        if _COMMON_INSTRUCTIONS_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
            return cached.text

        try:
            blob_service = BlobService(connection_string)
            instructions = blob_service.read_blob_text(container_name, blob_path)
            if instructions.strip():
                rendered = f"\n\n{instructions}"
                if _COMMON_INSTRUCTIONS_CACHE_TTL_SECONDS > 0:
                    _COMMON_INSTRUCTIONS_CACHE[cache_key] = _CachedCommonInstructions(
                        text=rendered,
                        expires_at=now + _COMMON_INSTRUCTIONS_CACHE_TTL_SECONDS,
                    )
                return rendered
            raise RuntimeError(f"FormSupportAgent common instructions blob {container_name}/{blob_path} is empty.")
        except Exception as e:
            raise RuntimeError(f"Failed to load FormSupportAgent common instructions from blob {container_name}/{blob_path}: {e}") from e


    async def run(self, userquery, session=None, thread=None):
        active_session = session or thread
        result = await self.agent.run(userquery, session=active_session)
        return result.text


async def dryrun(query):
    raise RuntimeError(
        "FormSupportAgent dryrun no longer reads tenant settings from .env. "
        "Invoke through the orchestrator so client_settings are resolved from Cosmos."
    )

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))    
           
