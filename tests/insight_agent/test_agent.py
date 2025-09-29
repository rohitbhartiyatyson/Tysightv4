import json
import pytest
from langchain.llms.fake import FakeListLLM
from insight_agent.agent import build_agent


def test_agent_flow(monkeypatch):
    # Prepare deterministic LLM responses for the agent steps
    # 1) intent_recognition_tool -> return JSON intent
    # 2) metric_selection_tool -> is pure code, no LLM call
    # 3) sql_generation_tool -> return JSON {"sql": "SELECT ..."}
    # 4) data_synthesis_tool -> return a short summary

    # LangChain planning LLM should emit actions in the ReAct format.
    planning_responses = [
        "Action: intent_recognition_tool\nAction Input: how did jimmy dean perform?",
        "Action: metric_selection_tool\nAction Input: performance_summary",
        "Action: sql_generation_tool\nAction Input: intent=performance_summary;entities={brand: Jimmy Dean};metrics=[dollar_sales]",
        "Action: data_synthesis_tool\nAction Input: df_head_sample",
        "Final Answer: Jimmy Dean saw a 10% increase in dollar sales."
    ]

    llm = FakeListLLM(responses=planning_responses)

    # Mock the underlying litellm.completion calls used by our tools to return tool observations
    import litellm
    tool_outputs = [
        json.dumps({"intent": "performance_summary", "entities": {"brand": "Jimmy Dean"}}),
        json.dumps({"sql": "SELECT dollar_sales FROM table WHERE brand='Jimmy Dean' LIMIT 10"}),
        "Jimmy Dean saw a 10% increase in dollar sales."
    ]

    def fake_completion(*args, **kwargs):
        # return the next pre-defined tool output
        return tool_outputs.pop(0)

    monkeypatch.setattr(litellm, 'completion', fake_completion)

    executor = build_agent(llm=llm)

    # Call the agent with a sample question using invoke
    out = executor.invoke({"input": "how did jimmy dean perform?"})
    result = json.dumps(out)

    # Ensure the final result contains the summary text we provided
    assert "Jimmy Dean saw a 10% increase in dollar sales" in result
