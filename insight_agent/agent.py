from langchain_core.runnables.base import RunnableLambda
from insight_agent.tools import (
    intent_recognition_tool,
    metric_selection_tool,
    sql_generation_tool,
    data_synthesis_tool,
)
from insight_agent.query_executor import execute_query
import pandas as pd
import json


def build_agent(llm=None):
    """Build a simple LCEL-style runnable that executes the pipeline deterministically:
    Intent -> Metrics -> SQL -> Run Query -> Summary

    The returned object implements .invoke(inputs) for compatibility with the UI.
    """

    def run_chain(inputs: dict):
        question = inputs.get('input')
        kind = inputs.get('kind') or ''

        intermediates = []

        # 1) Deterministic guard: if the question starts with a SQL SELECT, bypass the LLM
        parsed_intent = None
        if isinstance(question, str) and question.strip().lower().startswith('select'):
            parsed_intent = {"intent": "direct_sql_query", "entities": {}}
            intermediates.append(('intent', parsed_intent))
        else:
            # 1a) Intent recognition (LLM-backed tool)
            intent_json = intent_recognition_tool.func(question)
            try:
                parsed_intent = json.loads(intent_json) if isinstance(intent_json, str) else intent_json
            except Exception:
                parsed_intent = {"intent": "unknown", "entities": {}}
            intermediates.append(('intent', parsed_intent))

        intent = parsed_intent.get('intent') if isinstance(parsed_intent, dict) else str(parsed_intent)

        # 2) Branching logic: if intent indicates a direct SQL request, bypass metric selection
        if intent == 'direct_sql_query':
            intermediates.append(('branch', 'direct_sql'))
            # Directly ask the SQL generator to build SQL for the question
            sql_input = {
                'question': question,
                'kind': kind,
                'filters': inputs.get('filters') or inputs.get('selected_filters') or {},
                'metrics': [],
                'mode': 'generalist',
            }
            sql_result = sql_generation_tool.func(sql_input)
            # enforce contract: tool returns plain SQL string on success, or dict with error
            if isinstance(sql_result, dict) and 'error' in sql_result:
                intermediates.append(('error', sql_result))
                # do not proceed to execute
                return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
            else:
                sql_text = sql_result
                intermediates.append(('sql', sql_text))
        else:
            # 2a) Metric selection (code tool)
            metrics = metric_selection_tool.func(intent)
            intermediates.append(('metrics', metrics))

            # 3) SQL generation
            sql_input = {
                'question': question,
                'kind': kind,
                'filters': inputs.get('filters') or inputs.get('selected_filters') or {},
                'metrics': metrics,
                'mode': 'specialist',
            }
            sql_text = sql_generation_tool.func(sql_input)
            intermediates.append(('sql', sql_text))

        # 4) Execute SQL against DuckDB (using existing executor)
        df = pd.DataFrame()
        try:
            df = execute_query(kind, sql_text)
            intermediates.append(('query_result_head', df.head().to_string()))
        except Exception as e:
            intermediates.append(('query_error', str(e)))

        # 5) Summary
        df_head = df.head().to_string() if not df.empty else ''
        summary = data_synthesis_tool.func(df_head)
        intermediates.append(('summary', summary))

        return {
            'final_answer': summary,
            'intermediate_steps': intermediates,
        }

    return RunnableLambda(run_chain)
