import sys
import os
from dotenv import load_dotenv
import asyncio
from agent_framework.azure import AzureOpenAIChatClient

# Add parent directory to path to allow importing 'tools'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.azure_ai_search import azure_ai_search


load_dotenv()


class ConversationAgent:
    
    def __init__(self,endpoint, api_key):        
        self.agent = AzureOpenAIChatClient(endpoint=endpoint, api_key=api_key).create_agent(
            instructions=f"""
                You are an assistant for BC Government's Permit Application. Use the azure_ai_search tool to answer user queries.
                
                STRICT RULES:
                1. You must ONLY use the information provided by the azure_ai_search tool.                 
                2. If the azure_ai_search tool returns "No results found" or an empty result, return "Not found" immediately.
                3. Always include the metadata (Source and Processed with) from the azure_ai_search and all the azure_ai_search for the information you provide in your response.
                4. Format your response clearly, citing the source and processed with and all the azure_ai_search results at the end.
                5.If the query is related with a water permit or license application for usage below 24 months, then please suggest user to use other application called 'Short-term use of water approval application', link : https://j200.gov.bc.ca/pub/vfcbc/NewApplication.aspx?AppFormCode=WSEC8                               
            """,
            tools=azure_ai_search,
            name="ConversationAgent"
        ) 



    async def run(self, userquery):
        
        result = await self.agent.run(userquery)
        return result.text




async def dryrun(query):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    model =  os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    agent = ConversationAgent(endpoint,api_key)
  
    print("User Query is {0}".format(query))
    result = await agent.run(query)
    print(result)
    

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))    

