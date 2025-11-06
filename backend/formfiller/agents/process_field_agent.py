from ..llm_client import get_llm
from backend.formfiller.prompts.process_field_prompt import process_field_prompt
from langchain.chains import LLMChain

# Create a function that returns the LLMChain lazily
def get_process_field_executor():
    return LLMChain(
        llm=get_llm(),
        prompt=process_field_prompt,
        verbose=True
    )

# For backward compatibility, create a property-like access
class ProcessFieldExecutor:
    def __getattr__(self, name):
        return getattr(get_process_field_executor(), name)
    
    def __call__(self, *args, **kwargs):
        return get_process_field_executor()(*args, **kwargs)

process_field_executor = ProcessFieldExecutor()