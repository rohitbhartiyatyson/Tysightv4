import json
import litellm
from insight_agent.tools import sql_generation_tool


def test_get_sql_from_prompt_monkeypatch(monkeypatch):
    # Mock litellm.completion to return a JSON string
    def fake_completion(prompt, max_tokens=256):
        return json.dumps({"sql": "SELECT * FROM table WHERE a = 'x'"})

    monkeypatch.setattr(litellm, 'completion', fake_completion)

    sql = sql_generation_tool.func('irrelevant')
    assert "SELECT * FROM table" in sql
