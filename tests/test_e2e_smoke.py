import pytest
from insight_agent.agent import build_agent
import insight_agent.tools as tools
from insight_agent.sql_validator import normalize_sql, validate_sql

# Monkeypatch deterministic tools

def fake_intent(question):
    q=question.lower()
    if 'yoy' in q or 'year' in q:
        return '{"intent":"yoy_performance","entities":{}}'
    return '{"intent":"unknown","entities":{}}'

def fake_metrics(intent):
    return ['num_col']

def fake_sql_special(input_data):
    # minimal SQL obeying rails
    kind=input_data.get('kind')
    return "SELECT SUM(num_col) AS num_col FROM test_kind LIMIT 1000"

def fake_sql_general(input_data):
    q=input_data.get('question','')
    # correct non-canonical
    q=q.replace('numcol','num_col')
    return "SELECT num_col FROM test_kind WHERE LOWER(a)=LOWER('prod1') LIMIT 1000"


def fake_synth(s):
    return 'SYNTH'


def setup_monkeypatches():
    tools.intent_recognition_tool.func = lambda q: fake_intent(q)
    tools.metric_selection_tool.func = lambda i: fake_metrics(i)
    tools.sql_generation_tool.func = lambda inp: fake_sql_general(inp) if inp.get('mode')=='generalist' else fake_sql_special(inp)
    tools.data_synthesis_tool.func = lambda x: fake_synth(x)


def test_specialist_path():
    setup_monkeypatches()
    exe = build_agent()
    resp = exe.invoke({'input':'What is YoY for A?','kind':'test_kind'})
    # extract final sql
    sqls = [s for t,s in resp.get('intermediate_steps',[]) if t=='sql']
    assert sqls, 'no sql generated'
    sql = sqls[-1]
    # normalize and validate
    ns = normalize_sql(sql,'test_kind')
    validate_sql(ns,'test_kind')


def test_generalist_path():
    setup_monkeypatches()
    exe = build_agent()
    resp = exe.invoke({'input':'SELECT numcol FROM test_kind WHERE a = \"prod1\"','kind':'test_kind'})
    sqls = [s for t,s in resp.get('intermediate_steps',[]) if t=='sql']
    assert sqls
    sql = sqls[-1]
    ns = normalize_sql(sql,'test_kind')
    validate_sql(ns,'test_kind')
