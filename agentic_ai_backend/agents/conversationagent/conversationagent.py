import sys
import os
from dotenv import load_dotenv
import asyncio
from agent_framework.openai import OpenAIChatCompletionClient

# Add parent directory to path to allow importing 'tools'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.azure_ai_search import azure_ai_search


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


class ConversationAgent:
    
    def __init__(self, endpoint, api_key, deployment_name, api_version,max_tokens, temperature):
        client = AzureOpenAIChatClient(
            model=deployment_name,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        agent_kwargs = {
            "instructions": f"""
                You are an assistant for BC Government's Permit Application. Use the azure_ai_search tool to answer user queries.
                
                STRICT RULES:
                1. You must ONLY use the information provided by the azure_ai_search tool.                 
                2. If the azure_ai_search tool returns "No results found" or an empty result, return "Not found" immediately.
                3. Always include the metadata (Source and Processed with) from the azure_ai_search and all the azure_ai_search for the information you provide in your response.
                4. Format your response clearly, citing the source and processed with and all the azure_ai_search results at the end.
                6. Whenever you include a URL or web link in your response, always format it as a Markdown link using the syntax [descriptive text](url). Use meaningful link text that describes the destination. If no descriptive text is available, use [here](url).
            """,
            "tools": [azure_ai_search],
            "name": "ConversationAgent",
        }
        self.agent = client.as_agent(
            **agent_kwargs,
            default_options={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tool_choice": "required",
            },
        )


    async def run(self, userquery, session=None, thread=None):
        #active_session = session or thread #TODO: Decide on session management strategy with ConversationAgent. ABIN: Lets wait till agentic retreival Azure AI Search is fixed
        result = await self.agent.run(userquery)
        return result.text




async def dryrun(query):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    api_version = os.environ["AZURE_OPENAI_API_VERSION"]
    max_tokens = int(os.getenv("AGENT_MAX_TOKENS", "800"))
    temperature = float(os.getenv("AGENT_TEMPERATURE", "0.1"))
    agent = ConversationAgent(endpoint, api_key, deployment_name, api_version, max_tokens, temperature)
  
    print("User Query is {0}".format(query))
    result = await agent.run(query)
    print(result)
    

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))    

