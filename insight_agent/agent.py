from langchain_core.runnables.base import RunnableLambda
from insight_agent.tools import (
    intent_recognition_tool,
    metric_selection_tool,
    sql_generation_tool,
    data_synthesis_tool,
)
from insight_agent.contracts import IntentSchema
from insight_agent.query_executor import execute_query
import pandas as pd
import json
from insight_agent.llm_client import get_summary_from_df


def build_agent(llm=None):
    """Build a simple LCEL-style runnable that executes the pipeline deterministically:
    Intent -> Metrics -> SQL -> Run Query -> Summary

    The returned object implements .invoke(inputs) for compatibility with the UI.
    """

    def run_chain(inputs: dict):
        question = inputs.get('input')
        kind = inputs.get('kind') or ''

        intermediates = []

        # helper to append a top-level intermediate only if it's not already present
        def append_if_missing(key, value):
            try:
                for kk, vv in intermediates:
                    if kk == key:
                        return
            except Exception:
                pass
            intermediates.append((key, value))

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
            # enforce contract: tool may return dict with 'error' or structured results, or a plain SQL string
            if isinstance(sql_result, dict) and 'error' in sql_result:
                intermediates.append(('error', sql_result))
                # extract rails_status from several possible locations and emit top-level rails_status
                try:
                    rails_top = None
                    if isinstance(sql_result.get('rails_status'), dict):
                        rails_top = sql_result.get('rails_status')
                    elif isinstance(sql_result.get('sql'), dict) and isinstance(sql_result.get('sql').get('rails_status'), dict):
                        rails_top = sql_result.get('sql').get('rails_status')
                    intermediates.append(('rails_status', rails_top or {'preflight_complete': False, 'filters_enforced': False, 'predicates_applied': 0, 'validator_passed': False, 'fallback_used': False, 'failure_code': sql_result.get('error')}))
                except Exception:
                    pass
                # also surface prompts if provided
                try:
                    if isinstance(sql_result, dict) and sql_result.get('sql_llm_prompt'):
                        intermediates.append(('sql_llm_prompt', sql_result.get('sql_llm_prompt')))
                    if isinstance(sql_result, dict) and sql_result.get('sql_llm_output_raw'):
                        intermediates.append(('sql_llm_output_raw', sql_result.get('sql_llm_output_raw')))
                except Exception:
                    pass
                # ensure SQL LLM markers present if skipped
                try:
                    append_if_missing('sql_llm_prompt', "(skipped: error path)")
                    append_if_missing('sql_llm_output_raw', "(skipped)")
                except Exception:
                    pass
                # ensure unified query_exec present with error
                try:
                    append_if_missing('query_exec', {'engine': 'duckdb', 'binding': 'data', 'rows': 0, 'elapsed_ms': 0, 'error': f"sql_generation_error: {sql_result.get('error')}"})
                except Exception:
                    pass
                # ensure insights markers present
                try:
                    append_if_missing('insights_llm_prompt', "(skipped: error path)")
                    append_if_missing('insights_llm_output', f"skipped: {sql_result.get('error')}")
                except Exception:
                    pass
                # do not proceed to execute
                return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
            else:
                # sql_result may be a string or a dict containing sql info
                # normalize to extract SQL string and rails_status if present
                sql_str = None
                rails_top = None
                if isinstance(sql_result, dict):
                    nested = sql_result.get('sql')
                    if isinstance(nested, dict):
                        sql_str = nested.get('sql')
                        rails_top = nested.get('rails_status') or sql_result.get('rails_status')
                    else:
                        sql_str = nested if isinstance(nested, str) else None
                        rails_top = sql_result.get('rails_status')
                    # prefer to emit clean SQL string as the 'sql' intermediate
                    intermediates.append(('sql', sql_str or sql_result))
                    intermediates.append(('rails_status', rails_top))
                    try:
                        if 'sql_llm_prompt' in sql_result:
                            intermediates.append(('sql_llm_prompt', sql_result.get('sql_llm_prompt')))
                        if 'sql_llm_output_raw' in sql_result:
                            intermediates.append(('sql_llm_output_raw', sql_result.get('sql_llm_output_raw')))
                    except Exception:
                        pass
                    # set sql_text string for execution
                    if sql_str:
                        sql_text = sql_str
                    elif isinstance(nested, str):
                        sql_text = nested
                    else:
                        # fallback: coerce to string
                        sql_text = str(sql_result.get('sql'))
                else:
                    sql_text = sql_result
                    intermediates.append(('sql', sql_text))
                    # ensure rails_status top-level present (none info)
                    intermediates.append(('rails_status', None))
                    # mark SQL LLM skipped in deterministic template path
                    try:
                        append_if_missing('sql_llm_prompt', "(skipped: deterministic template)")
                        append_if_missing('sql_llm_output_raw', "(skipped)")
                    except Exception:
                        pass
        else:
            # 2a) Metric selection (code tool)
            metrics = metric_selection_tool.func(intent)
            # Metrics default for sales_performance when empty
            if intent == IntentSchema.sales_performance.value and not metrics:
                metrics = ["dollar_sales", "unit_sales", "volume_sales"]
            intermediates.append(('metrics', metrics))

            # Build and emit the plan after metrics so metrics count is accurate
            try:
                plan_summary = f"intent={intent} • metrics={len(metrics) if isinstance(metrics, (list,tuple)) else 0} • dims={len(inputs.get('dimensions') or inputs.get('dims') or []) if isinstance(inputs.get('dimensions') or inputs.get('dims') or [], (list,tuple)) else 0} • filters={len(inputs.get('filters') or {})} • engine=duckdb • table=data"
                intermediates.append(('plan', plan_summary))
            except Exception:
                pass

            # 3) Specialist deterministic bypass for known intents (compose SQL without LLM)
            bypassed = False
            if intent in (IntentSchema.sales_performance.value, IntentSchema.yoy_performance.value):
                bypassed = True
                try:
                    # compose deterministic SQL
                    dims = inputs.get('dimensions') or inputs.get('dims') or []
                    filters_local = inputs.get('filters') or inputs.get('selected_filters') or {}
                    from insight_agent.sql_validator import enforce_filters, normalize_sql, validate_sql
                    if intent == IntentSchema.sales_performance.value:
                        metrics_list = metrics or ["dollar_sales", "unit_sales", "volume_sales"]
                        select_parts = [f"SUM({m}) AS {m}" for m in metrics_list]
                    else:
                        # yoy_performance: find base metrics and their _ya counterparts
                        base_metrics = []
                        for m in metrics:
                            if m.endswith('_ya'):
                                base = m[:-3]
                                if base not in base_metrics:
                                    base_metrics.append(base)
                            else:
                                # only add if corresponding _ya in metrics
                                if f"{m}_ya" in metrics and m not in base_metrics:
                                    base_metrics.append(m)
                        if not base_metrics:
                            base_metrics = ["dollar_sales"]
                        select_parts = []
                        for b in base_metrics:
                            a = b
                            ya = f"{b}_ya"
                            select_parts.append(f"SUM({a}) AS {a}")
                            select_parts.append(f"SUM({ya}) AS {ya}")
                            select_parts.append(f"(SUM({a}) - SUM({ya})) AS {b}_delta")
                            select_parts.append(f"CASE WHEN SUM({ya}) IS NULL OR SUM({ya})=0 THEN NULL ELSE (SUM({a}) - SUM({ya})) * 1.0 / NULLIF(SUM({ya}),0) END AS {b}_pct_delta")
                    select_clause = ', '.join(select_parts)
                    sql_comp = f"SELECT {select_clause} FROM data"
                    # enforce filters and dims, ensure LIMIT 1000
                    sql_with_filters = enforce_filters(sql_comp + ' LIMIT 1000', filters_local or {})
                    if dims:
                        dims_clause = ', '.join(dims)
                        sql_with_filters = sql_with_filters.replace(' LIMIT 1000', f' GROUP BY {dims_clause} LIMIT 1000')
                    # normalize and validate
                    try:
                        sql_norm = normalize_sql(sql_with_filters, kind)
                    except Exception:
                        sql_norm = sql_with_filters
                    try:
                        validate_sql(sql_norm, kind, filters_local or {})
                        validator_passed = True
                    except Exception:
                        validator_passed = False
                    predicates_applied = sql_norm.count('LOWER(')
                    rails_status_final = {
                        'preflight_complete': True,
                        'filters_enforced': (predicates_applied>0),
                        'predicates_applied': predicates_applied,
                        'validator_passed': validator_passed,
                        'fallback_used': False,
                        'specialist_bypass': True,
                        'failure_code': None if validator_passed else 'VALIDATION_FAILED'
                    }
                    intermediates.append(('sql', sql_norm))
                    intermediates.append(('rails_status', rails_status_final))
                    append_if_missing('sql_llm_prompt', "(skipped: deterministic template)")
                    append_if_missing('sql_llm_output_raw', "(skipped)")
                    sql_text = sql_norm
                except Exception as e:
                    intermediates.append(('fallback_error', str(e)))
                    return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
            else:
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
            if not bypassed:
                if isinstance(sql_result, dict) and 'error' in sql_result:
                    err = sql_result.get('error')
                    intermediates.append(('error', sql_result))
                    # only attempt deterministic fallback for specialist intents
                    specialist_intents = {i.value for i in IntentSchema}
                    if err == 'INCOMPLETE_SQL' and intent in specialist_intents:
                        try:
                            # Build a basic SELECT using metrics determined earlier
                            def build_fallback(metrics_list, dims, filters_dict, kind_name):
                                if not metrics_list:
                                    metrics_list = ['dollar_sales']
                                select_parts = [f"SUM({m}) AS {m}" for m in metrics_list]
                                select_clause = ', '.join(select_parts)
                                base = f"SELECT {select_clause} FROM data"
                                from insight_agent.sql_validator import enforce_filters
                                sql_with_filters = enforce_filters(base + ' LIMIT 1000', filters_dict or {})
                                if dims:
                                    dims_clause = ', '.join(dims)
                                    sql_with_filters = sql_with_filters.replace(' LIMIT 1000', f' GROUP BY {dims_clause} LIMIT 1000')
                                return sql_with_filters

                            fallback_sql = build_fallback(metrics, sql_input.get('dimensions') or [], sql_input.get('filters') or {}, kind)
                            intermediates.append(('fallback_used', True))
                            try:
                                if isinstance(sql_result, dict):
                                    append_if_missing('sql_llm_prompt', sql_result.get('sql_llm_prompt') or "(skipped: fallback)")
                                    append_if_missing('sql_llm_output_raw', sql_result.get('sql_llm_output_raw') or "(skipped)")
                            except Exception:
                                pass

                            intermediates.append(('sql', fallback_sql))
                            try:
                                predicates_applied = fallback_sql.count('LOWER(')
                                try:
                                    from insight_agent.sql_validator import validate_sql
                                    try:
                                        validate_sql(fallback_sql, kind, sql_input.get('filters') or {})
                                        validator_passed = True
                                        failure_code = None
                                    except Exception:
                                        validator_passed = False
                                        failure_code = 'VALIDATION_FAILED'
                                except Exception:
                                    validator_passed = False
                                    failure_code = 'VALIDATION_FAILED'

                                rails_status_final = {
                                    'preflight_complete': True,
                                    'filters_enforced': (predicates_applied>0),
                                    'predicates_applied': predicates_applied,
                                    'validator_passed': validator_passed,
                                    'fallback_used': True,
                                    'failure_code': failure_code
                                }
                                intermediates.append(('rails_status', rails_status_final))
                            except Exception:
                                try:
                                    intermediates.append(('rails_status', {'preflight_complete': True, 'filters_enforced': True, 'predicates_applied': 0, 'validator_passed': False, 'fallback_used': True, 'failure_code': None}))
                                except Exception:
                                    pass

                            sql_text = fallback_sql
                        except Exception as e:
                            intermediates.append(('fallback_error', str(e)))
                            return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
                    else:
                        # For non-specialist intents, surface the incomplete rails_status and stop
                        try:
                            rails_top = None
                            if isinstance(sql_result.get('rails_status'), dict):
                                rails_top = sql_result.get('rails_status')
                            elif isinstance(sql_result.get('sql'), dict) and isinstance(sql_result.get('sql').get('rails_status'), dict):
                                rails_top = sql_result.get('sql').get('rails_status')
                            intermediates.append(('rails_status', rails_top or {'preflight_complete': False, 'filters_enforced': False, 'predicates_applied': 0, 'validator_passed': False, 'fallback_used': False, 'failure_code': err}))
                        except Exception:
                            pass
                        try:
                            append_if_missing('sql_llm_prompt', sql_result.get('sql_llm_prompt') or "(skipped: error path)")
                            append_if_missing('sql_llm_output_raw', sql_result.get('sql_llm_output_raw') or "(skipped)")
                        except Exception:
                            pass
                        try:
                            append_if_missing('query_exec', {'engine': 'duckdb', 'binding': 'data', 'rows': 0, 'elapsed_ms': 0, 'error': f"sql_generation_error: {err}"})
                        except Exception:
                            pass
                        try:
                            append_if_missing('insights_llm_prompt', "(skipped: error path)")
                            append_if_missing('insights_llm_output', f"skipped: {err}")
                        except Exception:
                            pass
                        return {'final_answer': 'Could not generate SQL', 'intermediate_steps': intermediates}
                else:
                    # Normalize structured sql_result when present
                    if isinstance(sql_result, dict):
                        nested = sql_result.get('sql')
                        sql_str = None
                        rails_top = None
                        if isinstance(nested, dict):
                            sql_str = nested.get('sql')
                            rails_top = nested.get('rails_status') or sql_result.get('rails_status')
                        else:
                            sql_str = nested if isinstance(nested, str) else None
                            rails_top = sql_result.get('rails_status')
                        intermediates.append(('sql', sql_str or sql_result))
                        intermediates.append(('rails_status', rails_top))
                        try:
                            if 'sql_llm_prompt' in sql_result:
                                intermediates.append(('sql_llm_prompt', sql_result.get('sql_llm_prompt')))
                            if 'sql_llm_output_raw' in sql_result:
                                intermediates.append(('sql_llm_output_raw', sql_result.get('sql_llm_output_raw')))
                            # ensure placeholders exist so UI/tests always see these markers
                            append_if_missing('sql_llm_prompt', sql_result.get('sql_llm_prompt') or "(skipped)")
                            append_if_missing('sql_llm_output_raw', sql_result.get('sql_llm_output_raw') or "(skipped)")
                        except Exception:
                            pass
                        if sql_str:
                            sql_text = sql_str
                        elif isinstance(nested, str):
                            sql_text = nested
                        else:
                            sql_text = str(sql_result.get('sql'))
                    else:
                        sql_text = sql_result
                        intermediates.append(('sql', sql_text))

        # 4) Execute SQL against DuckDB (using existing executor)
        df = pd.DataFrame()
        import time
        query_exec = None
        t0 = time.monotonic()
        try:
            df = execute_query(kind, sql_text)
            t1 = time.monotonic()
            rows = int(df.shape[0]) if hasattr(df, 'shape') else None
            preview = df.head(3).to_dict(orient='records') if not df.empty else []
            query_exec = {
                'engine': 'duckdb',
                'binding': 'data',
                'rows': rows,
                'elapsed_ms': int((t1 - t0) * 1000),
                'preview': preview,
            }
            intermediates.append(('query_exec', query_exec))
        except Exception as e:
            t1 = time.monotonic()
            query_exec = {
                'engine': 'duckdb',
                'binding': 'data',
                'rows': 0,
                'elapsed_ms': int((t1 - t0) * 1000),
                'error': str(e),
            }
            intermediates.append(('query_exec', query_exec))

        # 5) Summary
        try:
            df_head = df.head().to_string() if not df.empty else ''
        except Exception:
            df_head = str(df)

        # Build the summary prompt and emit insights markers before/after calling the summary LLM/tool
        try:
            cleaned_question = question.splitlines()[-1].strip() if isinstance(question, str) else str(question)
        except Exception:
            cleaned_question = str(question)
        summary_prompt = f"""Given the user's question, '{cleaned_question}', write a single, concise English sentence that summarizes the main finding in the data below.\n\n\nData:\n{df_head}\n"""

        try:
            # record the prompt as a top-level intermediate so UI always has the insights prompt
            append_if_missing('insights_llm_prompt', summary_prompt)
        except Exception:
            pass

        try:
            summary = data_synthesis_tool.func(df_head)
        except Exception as e:
            summary = f"Error: The AI summary could not be generated: {e}"

        try:
            append_if_missing('insights_llm_output', summary)
        except Exception:
            pass

        intermediates.append(('summary', summary))

        return {
            'final_answer': summary,
            'intermediate_steps': intermediates,
        }

    return RunnableLambda(run_chain)
