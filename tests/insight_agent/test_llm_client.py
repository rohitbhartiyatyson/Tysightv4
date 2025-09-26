import json
import litellm
from insight_agent.llm_client import get_sql_from_prompt


def test_get_sql_from_prompt_monkeypatch(monkeypatch):
    # Mock litellm.completion to return a JSON string
    def fake_completion(prompt, max_tokens=256):
        return json.dumps({"sql": "SELECT * FROM table WHERE a = 'x'"})

    monkeypatch.setattr(litellm, 'completion', fake_completion)

    sql = get_sql_from_prompt('irrelevant')
    assert "SELECT * FROM table" in sql
