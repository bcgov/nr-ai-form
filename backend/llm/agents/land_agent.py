"""
Land agent definition and executor setup.
"""
from langchain.agents import create_react_agent, AgentExecutor
from ..llm_client import llm
from backend.llm.tools.ai_search_tool import ai_search_tool
from backend.llm.prompts.land_prompt import land_prompt

land_tools = [ai_search_tool]
land_agent = create_react_agent(llm, land_tools, land_prompt)
land_executor = AgentExecutor(
    agent=land_agent,
    tools=land_tools,
    verbose=False,
    handle_parsing_errors=True,
    max_iterations=4,
)
