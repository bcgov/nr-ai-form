from ..llm_client import get_llm
from backend.formfiller.prompts.analyze_form_prompt import analyze_form_prompt 
from langchain.chains import LLMChain

# Create a function that returns the LLMChain lazily
def get_analyze_form_executor():
    return LLMChain(
        llm=get_llm(),
        prompt=analyze_form_prompt,
        verbose=True
    )

# For backward compatibility, create a property-like access
class AnalyzeFormExecutor:
    def __getattr__(self, name):
        return getattr(get_analyze_form_executor(), name)
    
    def __call__(self, *args, **kwargs):
        return get_analyze_form_executor()(*args, **kwargs)

analyze_form_executor = AnalyzeFormExecutor()