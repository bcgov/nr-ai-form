
import asyncio
from agent_framework.azure import AzureOpenAIChatClient
from dotenv import load_dotenv
import os
import sys
import json
from utils.formutils import get_form_context
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, handler

load_dotenv()

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

def resolve_agent_assets(step_identifier, form_definition_service=None, prompt_template_service=None):
    """
    Resolves form definition JSON and prompt template for a given step identifier.
    Returns (form_definition_dict, prompt_template_str, step_identifier)
    """
    print(f"Resolving assets for step: {step_identifier}")
    step_key = str(step_identifier)
    form_definition = None
    prompt_template = None
    
    # 1. Cloud/Service Path
    if form_definition_service and prompt_template_service:
        json_filename = f"{step_key}.json"
        md_filename = f"{step_key}.md"
        
        try:
            form_definition = form_definition_service.fetch_form_definition(json_filename)
            prompt_template = prompt_template_service.fetch_prompt_template(md_filename)
        except Exception as e:
            print(f"Warning: Contacting blob storage failed or services not ready: {e}")
        
    # 2. Use local files if Cloud didn't return anything
    if not form_definition or not prompt_template:
        # Try local path
        local_def_path = os.path.join("formdefinitions", f"{step_key}.json")
        local_prompt_path = os.path.join("prompttemplates", f"{step_key}.md")
        
        if os.path.exists(local_def_path):
            try:
                with open(local_def_path, "r", encoding="utf-8") as f:
                    form_definition = json.load(f)
            except Exception as e:
                print(f"Error reading local form definition: {e}")

        if os.path.exists(local_prompt_path):
            try:
                with open(local_prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read()
            except Exception as e:
                print(f"Error reading local prompt template: {e}")
                
    return form_definition, prompt_template, step_key
    



class FormSupportAgent():
    def __init__(self, endpoint, api_key, deployment_name, form_context_str, instructions):
        if not instructions:
            raise ValueError("Instructions (Skill MD) are required to initialize the FormSupportAgent.")
            
        final_instructions = instructions
        
        # Inject the form context into the template if the placeholder exists
        if "{form_context_str}" in final_instructions:
            final_instructions = final_instructions.replace("{form_context_str}", form_context_str)
        else:
            # If it's a completely custom prompt without the placeholder, 
            # we should probably still append the context so the AI knows the fields
            final_instructions = f"{final_instructions}\n\nHere is the form context:\n{form_context_str}"

        self.agent = AzureOpenAIChatClient(endpoint=endpoint, api_key=api_key, deployment_name=deployment_name).create_agent(
                instructions=final_instructions,                
                name="FormSupportAgent",                
            ) 



    async def run(self, userquery):
            result = await self.agent.run(userquery)
            return result.text


async def dryrun(query):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]

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
        prompt_template_service=prompt_service
    )

    if not step_form_definition:
        print(f"Form definition not found for identifier: {step_key}")
        return        
        
    print(f"Using form schema for step: {step_key}")
    form_context_str = get_form_context(step_form_definition)  

    if not custom_instructions:
        print(f"WARNING: No prompt template (.md) found for step: {step_identifier}. Step is required to have a specialized prompt.")
        return

    agent = FormSupportAgent(endpoint, api_key, deployment_name, form_context_str, instructions=custom_instructions)
  
    print("User Query is: {0}".format(actual_query))
    result = await agent.run(actual_query)
    print("\nResult:")
    print(result)
   

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))    
           

