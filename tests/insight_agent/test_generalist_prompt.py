import json
import litellm
from insight_agent.tools import sql_generation_tool


def test_generalist_prompt_monkeypatch(monkeypatch):
    # Simulate the LLM returning a compliant SQL JSON
    def fake_completion(*args, **kwargs):
        return json.dumps({"sql": "SELECT SUM(dollar_sales) AS dollar_sales FROM data WHERE LOWER(brand)=LOWER('Jimmy Dean') LIMIT 1000"})

    # Prevent early exit due to missing API key and patch the exact module paths
    monkeypatch.setenv('LITELLM_API_KEY', 'dummy')
    monkeypatch.setattr('insight_agent.tools.litellm.completion', fake_completion)

    input_data = {
        'question': 'Give me total sales for Jimmy Dean',
        'kind': 'NIQ POS',
        'filters': {'brand': 'Jimmy Dean'},
        'metrics': ['dollar_sales'],
        'mode': 'generalist',
    }

    sql = sql_generation_tool.func(input_data)
    assert 'LOWER(brand)=LOWER' in sql
    assert 'SUM(dollar_sales)' in sql
    assert sql.strip().endswith('LIMIT 1000')
