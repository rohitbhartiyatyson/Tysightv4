import json
import litellm
from insight_agent.tools import sql_generation_tool


def test_get_sql_from_prompt_monkeypatch(monkeypatch):
    # Mock litellm.completion to return a JSON string
    def fake_completion(*args, **kwargs):
        return json.dumps({"sql": "SELECT * FROM data WHERE a = 'x' LIMIT 1000"})

    # Ensure code doesn't early-return and patch module-level litellm used by tools
    monkeypatch.setenv('LITELLM_API_KEY', 'dummy')
    monkeypatch.setattr('insight_agent.tools.litellm.completion', fake_completion)

    sql = sql_generation_tool.func('irrelevant')
    assert "SELECT * FROM data" in sql
