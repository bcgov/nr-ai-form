
import asyncio
from agent_framework.azure import AzureOpenAIChatClient
from dotenv import load_dotenv
import os
import sys
import json
from utils.formutils import get_form_context
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, handler

load_dotenv()


class FormSupportAgent():
    def __init__(self,endpoint, api_key,deployment_name,form_context_str):
      
        self.agent = AzureOpenAIChatClient(endpoint=endpoint, api_key=api_key,deployment_name=deployment_name).create_agent(
                instructions=f"""
                        You are a form field suggestion assistant that maps user questions to form field IDs.
                        You are given a form field list in JSON object with a "properties" array. Each property has:
                        - "ID": the unique identifier
                        - "Title": a short field name
                        - "Description": a longer explanation
                        - "Options": a list of suggested values

                        Task:
                        1. Read the user's query.
                        2. Compare the user's query to the "Title" and "Description" of each property.
                        3. If the user's query contains any of the words or phrases or synonyms that match any words in the "Title" or "Description", return **only the "ID" and "Description" of the matching property.
                        4. If multiple matches, return the first matching ID, Description and SuggestedValues in the JSON format
                        5. If no property matches, return `No Match`
                        6. Based on user's query, pick one value from the Options list and name it as "SuggestedValue"
                        7. Output Format:Return the ID, Description and SuggestedValue in the JSON format

                        Here is the form field list to search through:
                        {form_context_str}
                        """,                
                name="FormSupportAgent",                
            ) 



    async def run(self, userquery):
            result = await self.agent.run(userquery)
            return result.text


async def dryrun(query):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    model =  os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    # Load Form Definitions
    json_path = os.path.join("formdefinitions", "step2.json") #TODO: This shoud come form a form or blob store
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return        
    form_context_str = get_form_context(json_path)  
    agent = FormSupportAgent(endpoint,api_key,deployment_name,form_context_str)
  
    print("User Query is {0}".format(query))
    result = await agent.run(query)
    print(result)
   

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))    
           

