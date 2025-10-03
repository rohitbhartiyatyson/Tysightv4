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
            # enforce contract: tool returns dict with either 'error' or structured results
            if isinstance(sql_result, dict) and 'error' in sql_result:
                intermediates.append(('error', sql_result))
                # always emit top-level rails_status if present
                try:
                    rails = sql_result.get('rails_status')
                    intermediates.append(('rails_status', rails))
                except Exception:
                    pass
                # do not proceed to execute
                return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
            else:
                # sql_result may be a string or a dict containing sql info
                sql_text = sql_result
                intermediates.append(('sql', sql_text))
                # if tool returned structured dict, emit rails_status and prompts at top-level
                if isinstance(sql_result, dict):
                    try:
                        # emit rails_status as top-level for UI convenience
                        rails = sql_result.get('rails_status')
                        intermediates.append(('rails_status', rails))
                    except Exception:
                        pass
                    try:
                        if 'sql_llm_prompt' in sql_result:
                            intermediates.append(('sql_llm_prompt', sql_result.get('sql_llm_prompt')))
                        if 'sql_llm_output_raw' in sql_result:
                            intermediates.append(('sql_llm_output_raw', sql_result.get('sql_llm_output_raw')))
                    except Exception:
                        pass
        else:
            # 2a) Metric selection (code tool)
            metrics = metric_selection_tool.func(intent)
            intermediates.append(('metrics', metrics))

            # Build and emit the plan after metrics so metrics count is accurate
            try:
                plan_summary = f"intent={intent} • metrics={len(metrics) if isinstance(metrics, (list,tuple)) else 0} • dims=0 • filters={len(inputs.get('filters') or {})} • engine=duckdb • table=data"
                intermediates.append(('plan', plan_summary))
            except Exception:
                pass

            # 3) SQL generation
            sql_input = {
                'question': question,
                'kind': kind,
                'filters': inputs.get('filters') or inputs.get('selected_filters') or {},
                'metrics': metrics,
                'mode': 'specialist',
            }
            sql_result = sql_generation_tool.func(sql_input)
            # If tool signals INCOMPLETE_SQL, attempt deterministic fallback for specialist intents
            if isinstance(sql_result, dict) and 'error' in sql_result:
                err = sql_result.get('error')
                intermediates.append(('error', sql_result))
                if err == 'INCOMPLETE_SQL':
                    # Build deterministic fallback only for specialist intents
                    try:
                        # Build a basic SELECT using metrics determined earlier
                        def build_fallback(metrics_list, dims, filters_dict, kind_name):
                            if not metrics_list:
                                # fallback to a safe metric if none (should not happen in real flow)
                                metrics_list = ['dollar_sales']
                            # Build select clause: keep YOY pairs when present
                            select_parts = []
                            for m in metrics_list:
                                # if metric appears to be a metric alias, just include SUM(metric) as metric
                                select_parts.append(f"SUM({m}) AS {m}")
                            select_clause = ', '.join(select_parts)
                            base = f"SELECT {select_clause} FROM data"
                            # Enforce filters using enforcer
                            from insight_agent.sql_validator import enforce_filters
                            sql_with_filters = enforce_filters(base + ' LIMIT 1000', filters_dict or {})
                            # If dimensions present, add GROUP BY
                            if dims:
                                dims_clause = ', '.join(dims)
                                # insert GROUP BY before LIMIT
                                sql_with_filters = sql_with_filters.replace(' LIMIT 1000', f' GROUP BY {dims_clause} LIMIT 1000')
                            return sql_with_filters

                        fallback_sql = build_fallback(metrics, sql_input.get('dimensions') or [], sql_input.get('filters') or {}, kind)
                        intermediates.append(('fallback_used', True))
                        intermediates.append(('sql', fallback_sql))
                        sql_text = fallback_sql
                    except Exception as e:
                        intermediates.append(('fallback_error', str(e)))
                        return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
                else:
                    return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
            else:
                sql_text = sql_result
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
