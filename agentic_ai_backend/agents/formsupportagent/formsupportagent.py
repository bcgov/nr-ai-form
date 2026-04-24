
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

def resolve_agent_assets(step_identifier, form_definition_service=None, prompt_template_service=None):
    """
    Resolves form definition JSON and prompt template for a given step identifier.
    Returns (form_definition_dict, prompt_template_str, step_identifier)
    """
    print(f"Resolving assets for step: {step_identifier}")
    step_key = str(step_identifier)
    
    # 1. Cloud/Service Path
    if form_definition_service and prompt_template_service:
        json_filename = f"{step_key}.json"
        md_filename = f"{step_key}.md"
        
        form_definition = form_definition_service.fetch_form_definition(json_filename)
        prompt_template = prompt_template_service.fetch_prompt_template(md_filename)
        
        return form_definition, prompt_template, step_key

    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "formdefinitions", f"{step_key}.json")
    prompt_path = os.path.join(base_dir, "prompttemplates", f"{step_key}.md")

    resolved_json = json_path if os.path.exists(json_path) else None
    resolved_prompt = prompt_path if os.path.exists(prompt_path) else None

    return resolved_json, resolved_prompt, step_key



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
        

        # Append strict JSON formatting rule
        json_enforcement_rule = (
                "\n\nCRITICAL INSTRUCTION: Your response MUST be valid JSON only. "
                "NEVER wrap your response in markdown code blocks like ```json ... ```. "
                "Output raw JSON that can be parsed directly by JSON.parse()."
            )
        
        final_instructions += json_enforcement_rule
        final_instructions += (
                "\n\n CRITICAL INSTRUCTION: If the user provides livestock type, livestock count, and a time period "
                "(days, weeks, months, or years), use the livestock water consumption tools "
                "to calculate water demand in cubic meters (m3) and application fees."
            )

        client = AzureOpenAIChatClient(
            model=deployment_name,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        agent_kwargs = {
            "instructions": final_instructions,
            "tools": LIVESTOCK_WATER_CONSUMPTION_TOOLS,
            "name": "FormSupportAgent",
        }
        self.agent = client.as_agent(
            **agent_kwargs,
            default_options={"temperature": 0.1},
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

    step_form_definition, custom_instructions, step_key = resolve_agent_assets(step_identifier)
    if (not step_form_definition or not custom_instructions) and form_def_service and prompt_service:
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
           
