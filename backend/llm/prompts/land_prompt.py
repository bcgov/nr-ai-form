from langchain.prompts import PromptTemplate

land_prompt = PromptTemplate.from_template(
    "You are the Land agent. You can use tools to answer the user's request.\n\n"
    "You have access to the following tools:\n{tools}\n\n"
    "When deciding what to do, follow this format exactly:\n"
    "Question: the input question you must answer\n"
    "Thought: you should always think about what to do\n"
    "Action: the action to take, must be one of [{tool_names}]\n"
    "Action Input: the input to the action\n"
    "Observation: the result of the action\n"
    "... (this Thought/Action/Action Input/Observation cycle can repeat) ...\n"
    "Thought: I now know the final answer\n"
    "Final Answer: the final answer to the original input question\n\n"
    "Begin!\n\n"
    "Question: {input}\n"
    "{agent_scratchpad}"
)
