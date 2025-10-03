Objective: Harden SQL generation and add deterministic specialist bypass for key intents.

Summary:
- Hardened the SQL LLM prompt to present canonical snake_case schema only, require symmetric LOWER(...) comparisons, include a single micro-example, and instruct strict JSON output of the form {"sql": "<query>"}.
- Use deterministic LLM call params (temperature=0.0, higher max_tokens) and best-effort JSON-mode; provider errors now return structured {"error": "PROVIDER_ERROR: ..."}.
- Implemented deterministic specialist bypass in agent for sales_performance and yoy_performance that composes SQL programmatically (no SQL LLM call). The bypass still emits sql_llm_prompt="(skipped: deterministic template)" and sql_llm_output_raw="(skipped)", and rails_status includes specialist_bypass=true.
- Ensured the agent produces consistent top-level evidence intermediates: plan, rails_status, sql, query_exec, sql_llm_prompt, sql_llm_output_raw, insights_llm_prompt, insights_llm_output.

Files changed (high-level):
- insight_agent/tools.py -- SQL prompt/schema hardening and deterministic JSON-mode LLM call; provider error handling
- insight_agent/agent.py -- deterministic specialist bypass, metrics defaulting for sales_performance, consistent evidence emission
- tests/insight_agent/test_specialist_bypass.py -- new focused tests for specialist/generalist scenarios
- runs/evidence_dump_bypass.json -- smoke run evidence for the 'summarize the performance' case

How to reproduce locally:
1. Checkout branch feat/sql-hardening-specialist-bypass
2. Install deps: python -m pip install -e .[test]
3. Run focused tests: pytest -q tests/insight_agent/test_specialist_bypass.py
4. To run the deterministic smoke run (example):
   python -c "from insight_agent.agent import build_agent; import insight_agent.tools as tools; import json; tools.intent_recognition_tool.func=lambda q: json.dumps({'intent':'sales_performance','entities':{}}); tools.metric_selection_tool.func=lambda i: ['dollar_sales','unit_sales','volume_sales']; exe=build_agent(); print(exe.invoke({'input':'summarize the performance','kind':'NIQ POS','filters':{'market':'Total US xAOC','time_agg':'Latest 52 Wks - w/e 08/16/25','category':'BACON','brand':'WRIGHT'}}))"

PR: https://github.com/rohitbhartiyatyson/Tysightv4/pull/45

Status: Tests added and focused test suite for specialist bypass passes locally in the container. Smoke run evidence written to runs/evidence_dump_bypass.json.
