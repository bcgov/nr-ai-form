"""
Azure OpenAI LLM client and initialization logic for agentic flows.
"""
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

# Initialize the Azure OpenAI LLM
llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    openai_api_version="2024-12-01-preview",
)
