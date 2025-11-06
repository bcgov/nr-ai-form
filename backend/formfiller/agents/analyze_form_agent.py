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
# ReAct agent for future development
# from backend.llm.tools.ai_search_tool import ai_search_tool
# from ..llm_client import llm
# from langchain.agents import create_react_agent, AgentExecutor
# from backend.formfiller.prompts.analyze_form_prompt_ReAct import analyze_form_prompt

# analyze_form_tools = [ai_search_tool]

# analyze_form_agent = create_react_agent(llm, analyze_form_tools, analyze_form_prompt)

# analyze_form_executor = AgentExecutor(
#     agent=analyze_form_agent,
#     tools=analyze_form_tools,
#     verbose=True,
#     handle_parsing_errors=True,
#     max_iterations=5,
#     return_intermediate_steps=True,
# )