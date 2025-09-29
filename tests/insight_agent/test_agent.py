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

    fake_responses = [
        json.dumps({"intent": "performance_summary", "entities": {"brand": "Jimmy Dean"}}),
        json.dumps({"sql": "SELECT dollar_sales FROM table WHERE brand='Jimmy Dean' LIMIT 10"}),
        "Jimmy Dean saw a 10% increase in dollar sales."
    ]

    llm = FakeListLLM(responses=fake_responses)
    executor = build_agent(llm=llm)

    # Call the agent with a sample question
    result = executor.run("how did jimmy dean perform?")

    # Ensure the final result contains the summary text we provided
    assert "Jimmy Dean saw a 10% increase in dollar sales" in result
