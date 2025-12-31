
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

def resolve_agent_assets(step_identifier):
    """
    Locates the JSON schema and Markdown prompt template for a given step identifier.
    Returns (json_path, prompt_path, step_identifier)
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    form_defs_dir = os.path.join(base_dir, "formdefinitions")
    prompt_templates_dir = os.path.join(base_dir, "prompttemplates")
    
    step_key = str(step_identifier)
    possible_filenames = [
        f"{step_key}.json",
        f"step{step_key}.json",
        f"{step_key}" if step_key.endswith(".json") else f"{step_key}.json"
    ]
    
    json_path = None
    # 1. Try direct patterns
    for fname in possible_filenames:
        tmp_path = os.path.join(form_defs_dir, fname)
        if os.path.exists(tmp_path):
            json_path = tmp_path
            break
            
    # 2. Try prefix matching
    if not json_path:
        for fname in os.listdir(form_defs_dir):
            if fname.startswith(f"step{step_key}-") or fname.startswith(f"{step_key}-"):
                json_path = os.path.join(form_defs_dir, fname)
                break

    if not json_path:
        return None, None, step_key

    # 3. Resolve prompt path (.md ONLY)
    prompt_filename = os.path.basename(json_path).replace(".json", ".md")
    prompt_path = os.path.join(prompt_templates_dir, prompt_filename)
    if not os.path.exists(prompt_path):
        prompt_path = None
            
    return json_path, prompt_path, step_key


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

    step_identifier, actual_query = extract_step_from_query(query)

    if not step_identifier:
        print("WARNING: Step identifier is required. Please use the format 'step-name: query'")
        return

    json_path, prompt_path, step_key = resolve_agent_assets(step_identifier)

    if not json_path:
        print(f"Form definition file not found for identifier: {step_key}")
        return        
        
    print(f"Using form schema: {os.path.basename(json_path)}")
    form_context_str = get_form_context(json_path)  

    custom_instructions = None
    if prompt_path:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            custom_instructions = f.read()
            print(f"Loaded custom instructions from {os.path.basename(prompt_path)}")

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
           

