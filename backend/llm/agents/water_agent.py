"""
Water agent definition and executor setup.
"""
from langchain.agents import create_react_agent, AgentExecutor
from ..llm_client import llm
from backend.llm.tools.ai_search_tool import ai_search_tool
from backend.llm.prompts.water_prompt import water_prompt

water_tools = [ai_search_tool]
water_agent = create_react_agent(llm, water_tools, water_prompt)
water_executor = AgentExecutor(
    agent=water_agent,
    tools=water_tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=20,
    return_intermediate_steps=True,
)

