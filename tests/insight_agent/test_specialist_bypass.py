import json
import pytest
from insight_agent.agent import build_agent
import insight_agent.tools as tools

# Helper to run agent with monkeypatched intent/metrics

def run_with_intent(intent_name, metrics=None, kind='NIQ POS', filters=None, dimensions=None):
    # patch intent recognizer to return the desired intent
    tools.intent_recognition_tool.func = lambda q: json.dumps({"intent": intent_name, "entities": {}, "dimensions": dimensions or []})
    if metrics is not None:
        tools.metric_selection_tool.func = lambda i: metrics
    exe = build_agent()
    return exe.invoke({"input": "dummy question", "kind": kind, "filters": filters or {}, "dimensions": dimensions or []})


def test_specialist_bypass_sales(monkeypatch):
    # sales_performance should bypass LLM and compose deterministic SQL
    resp = run_with_intent('sales_performance', metrics=['dollar_sales','unit_sales','volume_sales'], filters={'market':'Total US xAOC','time_agg':'Latest 52 Wks - w/e 08/16/25','category':'BACON','brand':'WRIGHT'})
    steps = dict(resp.get('intermediate_steps',[]))
    assert 'sql' in steps
    assert 'rails_status' in steps
    rails = steps['rails_status']
    assert rails.get('specialist_bypass') is True
    assert rails.get('fallback_used') is False
    assert "LIMIT 1000" in steps['sql']
    assert steps.get('sql_llm_prompt') == "(skipped: deterministic template)" or steps.get('sql_llm_prompt') is None
    assert steps.get('sql_llm_output_raw') == "(skipped)" or steps.get('sql_llm_output_raw') is None


def test_specialist_bypass_yoy(monkeypatch):
    # yoy_performance should produce metric, metric_ya, delta and pct_delta
    metrics = ['dollar_sales','dollar_sales_ya']
    resp = run_with_intent('yoy_performance', metrics=metrics, filters={'market':'Total US xAOC'})
    steps = dict(resp.get('intermediate_steps',[]))
    sql = steps.get('sql','')
    assert 'dollar_sales' in sql
    assert 'dollar_sales_ya' in sql
    assert '_delta' in sql and '_pct_delta' in sql
    rails = steps.get('rails_status')
    assert rails.get('specialist_bypass') is True


def test_generalist_success(monkeypatch):
    # Mock sql_generation_tool to return valid JSON dict
    def fake_sql(inp):
        return {"sql":"SELECT SUM(dollar_sales) AS dollar_sales FROM data WHERE LOWER(brand)=LOWER('X') LIMIT 1000", "rails_status": {"preflight_complete":True}}
    monkeypatch.setattr(tools.sql_generation_tool, 'func', fake_sql)
    tools.intent_recognition_tool.func = lambda q: json.dumps({"intent": "unknown", "entities": {}})
    tools.metric_selection_tool.func = lambda i: ['dollar_sales']
    resp = build_agent().invoke({"input":"q","kind":"NIQ POS","filters":{}})
    steps = dict(resp.get('intermediate_steps',[]))
    assert 'sql' in steps
    assert 'rails_status' in steps
    assert steps.get('sql_llm_output_raw') is not None or steps.get('sql_llm_prompt') is not None


def test_generalist_incomplete(monkeypatch):
    # sql tool returns INCOMPLETE_SQL error
    def fake_sql_incomplete(inp):
        return {"error":"INCOMPLETE_SQL", "rails_status": {"preflight_complete": False}}
    monkeypatch.setattr(tools.sql_generation_tool, 'func', fake_sql_incomplete)
    tools.intent_recognition_tool.func = lambda q: json.dumps({"intent": "unknown", "entities": {}})
    tools.metric_selection_tool.func = lambda i: []
    resp = build_agent().invoke({"input":"q","kind":"NIQ POS","filters":{}})
    steps = dict(resp.get('intermediate_steps',[]))
    # Expect an error intermediate and top-level rails_status with preflight_complete False
    assert any(t=='error' for t,_ in resp.get('intermediate_steps',[]))
    rails = steps.get('rails_status')
    assert rails is not None
    assert rails.get('preflight_complete') is False
