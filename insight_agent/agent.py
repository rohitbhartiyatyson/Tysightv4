from langchain.agents import create_react_agent, AgentExecutor
from langchain.llms.fake import FakeListLLM

from insight_agent.tools import (
    intent_recognition_tool,
    metric_selection_tool,
    sql_generation_tool,
    data_synthesis_tool,
)

from langchain_core.prompts import PromptTemplate

SYSTEM_PROMPT_TEMPLATE = '''You are an analyst agent. When given a user question, follow this sequence:
1) Use the intent_recognition_tool to identify intent and entities from the user's question.
2) Use the metric_selection_tool with the intent to select relevant metrics.
3) Use the sql_generation_tool to generate SQL given intent, entities, and selected metrics.
4) Use the data_synthesis_tool to summarize results from the returned dataframe head.

Call tools only as needed and format outputs appropriately.

You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}'''


def build_agent(llm=None):
    # Use a FakeListLLM by default for deterministic responses in tests if not provided
    if llm is None:
        llm = FakeListLLM(responses=["RESPONSE_PLACEHOLDER"])

    tools = [intent_recognition_tool, metric_selection_tool, sql_generation_tool, data_synthesis_tool]
    prompt = PromptTemplate.from_template(SYSTEM_PROMPT_TEMPLATE)
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    # AgentExecutor wraps the agent into a runnable executor
    executor = AgentExecutor.from_agent_and_tools(agent, tools, verbose=True, handle_parsing_errors=True)
    return executor
