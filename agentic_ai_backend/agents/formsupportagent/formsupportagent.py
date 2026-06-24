
import asyncio
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import os
import sys
from utils.formutils import get_form_context

load_dotenv()


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
    print(f"Resolving assets for step: {step_identifier}")
    step_key = str(step_identifier)
    if not form_definition_service or not prompt_template_service:
        print("Azure Blob Storage asset services are unavailable; cannot resolve form assets.")
        return None, None, step_key

    json_filename = f"{step_key}.json"
    md_filename = f"{step_key}.md"
    
    form_definition = form_definition_service.fetch_form_definition(json_filename)
    prompt_template = prompt_template_service.fetch_prompt_template(md_filename)

    return form_definition, prompt_template, step_key



class FormSupportAgent():
    def __init__(self, endpoint, api_key, deployment_name, api_version, form_context_str, instructions):
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
                
        except Exception as e:
            final_instructions = f"{final_instructions}\n\nHere is the form context:\n{form_context_str}"
            print(f"Error processing instructions template: {e}")
        

        # Append shared FormSupportAgent rules (strict JSON-only output + livestock
        # tooling), loaded from Blob Storage with a local instructions.md fallback.
        final_instructions += self._load_common_instructions()

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

    def _load_common_instructions(self) -> str:
        """Load shared FormSupportAgent rules (JSON-only output + livestock tooling).

        Reads the blob at ``AGENT_FORMSUPPORTINSTRUCTION_PATH`` inside the
        ``AZURE_BLOBSTORAGE_CONTAINER`` container, using the connection string
        ``AZURE_BLOBSTORAGE_CONNECTIONSTRING`` (see ``.env``). Falls back to the
        bundled local ``instructions.md`` when the blob store is not configured
        or unreachable. The returned text is prefixed with a blank line so it can
        be appended directly to the step instructions.
        """
        connection_string = os.getenv("AZURE_BLOBSTORAGE_CONNECTIONSTRING")
        container_name = os.getenv("AZURE_BLOBSTORAGE_CONTAINER")
        blob_path = os.getenv("AGENT_FORMSUPPORTINSTRUCTION_PATH")

        if connection_string and container_name and blob_path:
            try:
                blob_service = BlobService(connection_string)
                instructions = blob_service.read_blob_text(container_name, blob_path)
                if instructions.strip():
                    print(f"Loaded FormSupportAgent common instructions from blob: {container_name}/{blob_path}")
                    return f"\n\n{instructions}"
                print(f"Blob {container_name}/{blob_path} is empty; falling back to local instructions.")
            except Exception as e:
                print(f"Failed to load common instructions from blob {container_name}/{blob_path}: {e}")
        else:
            print(
                "AZURE_BLOBSTORAGE_CONNECTIONSTRING/AZURE_BLOBSTORAGE_CONTAINER/"
                "AGENT_FORMSUPPORTINSTRUCTION_PATH not fully set; falling back to local instructions."
            )

        return self._load_local_common_instructions()

    @staticmethod
    def _load_local_common_instructions() -> str:
        local_path = os.path.join(os.path.dirname(__file__), "instructions.md")
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                instructions = f.read()
            if instructions.strip():
                print(f"Loaded FormSupportAgent common instructions from local file: {local_path}")
                return f"\n\n{instructions}"
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Failed to read local common instructions {local_path}: {e}")
        raise RuntimeError(
            "FormSupportAgent common instructions not found. Set "
            "AZURE_BLOBSTORAGE_CONNECTIONSTRING, AZURE_BLOBSTORAGE_CONTAINER, and "
            f"AGENT_FORMSUPPORTINSTRUCTION_PATH, or provide a local file at {local_path}."
        )

    async def run(self, userquery, session=None, thread=None):
        active_session = session or thread
        result = await self.agent.run(userquery, session=active_session)
        return result.text


async def dryrun(query):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    api_version = os.environ["AZURE_OPENAI_API_VERSION"]

    # Initialize Services
    connection_string = os.getenv("AZURE_BLOBSTORAGE_CONNECTIONSTRING")
    container_name = os.getenv("AZURE_BLOBSTORAGE_CONTAINER")
    
    blob_service = None
    form_def_service = None
    prompt_service = None
    
    if connection_string and container_name:
        try:
            blob_service = BlobService(connection_string)
            form_def_service = FormDefinitionService(blob_service, container_name)
            prompt_service = PromptTemplateService(blob_service, container_name)
            print(f"Initialized Blob Services for container: {container_name}")
        except Exception as e:
            print(f"Failed to initialize Blob Services: {e}")
           

    step_identifier, actual_query = extract_step_from_query(query)

    if not step_identifier:
        print("WARNING: Step identifier is required. Please use the format 'step-name: query'")
        return

    step_form_definition, custom_instructions, step_key = resolve_agent_assets(
        step_identifier,
        form_definition_service=form_def_service,
        prompt_template_service=prompt_service,
    )

    if not step_form_definition:
        print(f"Form definition file not found for identifier: {step_key}")
        return        

    print(f"Using form schema: {step_key}.json")
    form_context_str = get_form_context(step_form_definition)  

    if not custom_instructions:
        print(f"WARNING: No prompt template (.md) found for step: {step_identifier}. Step is required to have a specialized prompt.")
        return

    print(f"Loaded custom instructions from {step_key}.md")

    agent = FormSupportAgent(
        endpoint,
        api_key,
        deployment_name,
        api_version,
        form_context_str,
        instructions=custom_instructions,
    )
  
    print("User Query is: {0}".format(actual_query))
    result = await agent.run(actual_query)
    print("\nResult:")
    print(result)
   

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))    
           
