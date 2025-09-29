from langchain.agents import create_react_agent, AgentExecutor
from langchain.llms.fake import FakeListLLM

from insight_agent.tools import (
    intent_recognition_tool,
    metric_selection_tool,
    sql_generation_tool,
    data_synthesis_tool,
)

SYSTEM_PROMPT = '''You are an analyst agent. When given a user question, follow this sequence:
1) Use the intent_recognition_tool to identify intent and entities from the user's question.
2) Use the metric_selection_tool with the intent to select relevant metrics.
3) Use the sql_generation_tool to generate SQL given intent, entities, and selected metrics.
4) Use the data_synthesis_tool to summarize results from the returned dataframe head.

Call tools only as needed and format outputs appropriately.'''


def build_agent(llm=None):
    # Use a FakeListLLM by default for deterministic responses in tests if not provided
    if llm is None:
        llm = FakeListLLM(responses=["RESPONSE_PLACEHOLDER"])

    tools = [intent_recognition_tool, metric_selection_tool, sql_generation_tool, data_synthesis_tool]
    agent = create_react_agent(llm=llm, tools=tools, prompt=SYSTEM_PROMPT)
    # AgentExecutor wraps the agent into a runnable executor
    executor = AgentExecutor.from_agent_and_tools(agent, tools, verbose=True)
    return executor
