"""
Azure OpenAI LLM client and initialization logic for agentic flows.
"""
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

_llm_instance = None

def get_llm():
    """Lazy initialization of Azure OpenAI LLM client."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            openai_api_version="2024-12-01-preview",
        )
    return _llm_instance

# Backward compatibility proxy
class ModuleLLM:
    def __getattr__(self, name):
        return getattr(get_llm(), name)
    
    def __call__(self, *args, **kwargs):
        return get_llm()(*args, **kwargs)
    
    def __repr__(self):
        return f"ModuleLLM(proxy_for={get_llm().__class__.__name__})"
    
    def __getstate__(self):
        return {}
    
    def __setstate__(self, state):
        pass

# Create a lazy-loading instance that behaves like the actual LLM
llm = ModuleLLM()

