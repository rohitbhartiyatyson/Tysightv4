import json
import litellm
from insight_agent.tools import sql_generation_tool


def test_get_sql_from_prompt_monkeypatch(monkeypatch):
    # Mock litellm.completion to return a JSON string
    def fake_completion(*args, **kwargs):
        return json.dumps({"sql": "SELECT * FROM data WHERE a = 'x' LIMIT 1000"})

    monkeypatch.setenv('LITELLM_API_KEY', 'dummy')
    monkeypatch.setattr('insight_agent.tools.litellm.completion', fake_completion)

    sql = sql_generation_tool.func('irrelevant')
    assert isinstance(sql, str)
    assert "SELECT * FROM data" in sql
