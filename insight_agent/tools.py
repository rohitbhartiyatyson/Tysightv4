from langchain.tools import tool
import os
import json
import litellm
from insight_agent.contracts import IntentSchema

from dotenv import load_dotenv
load_dotenv()


@tool
def sql_generation_tool(input_data) -> str:
    """Generate SQL given a structured input dict containing:
    {
        "question": str,
        "kind": str,
        "filters": dict,
        "metrics": list  (optional)
    }

    This tool will load the kind schema where possible and build a comprehensive
    prompt including schema, filters, metrics and the user's question before
    calling the LLM. For backward compatibility, if a string is passed it will
    be treated as the prompt body directly.
    """
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    if not api_key:
        return "Error: LITELLM_API_KEY is not set. Please create a .env file with your API key."

    # Accept raw prompt strings for backward compatibility
    filters = {}

    if isinstance(input_data, str):
        prompt = input_data
    else:
        # expected a dict-like input
        question = input_data.get('question') or input_data.get('input') or ''
        kind = input_data.get('kind') or ''
        filters = input_data.get('filters') or input_data.get('selected_filters') or {}
        metrics = input_data.get('metrics') or []

        # Try to load a schema from domain/catalog/kinds/<kind>/v*/mapping_effective.json
        schema_lines = []
        if kind:
            kinds_base = os.path.join('domain', 'catalog', 'kinds')
            kind_dir = os.path.join(kinds_base, kind)
            if os.path.exists(kind_dir):
                # pick the latest v* folder if present
                try:
                    versions = [d for d in os.listdir(kind_dir) if os.path.isdir(os.path.join(kind_dir, d))]
                    versions = sorted(versions)
                    for v in reversed(versions):
                        eff = os.path.join(kind_dir, v, 'mapping_effective.json')
                        if os.path.exists(eff):
                            try:
                                with open(eff, 'r') as fh:
                                    mapping = json.load(fh)
                                    # mapping_effective.json expected to be a list or dict of mappings
                                    if isinstance(mapping, dict):
                                        for k, v in mapping.items():
                                            # prefer canonical_name when available
                                            canon = v.get('canonical_name') or k
                                            schema_lines.append(f"{canon}: {v.get('data_type','unknown')}")
                                    else:
                                        # fallback when list
                                        for entry in mapping:
                                            canon = entry.get('canonical_name') or entry.get('original_name')
                                            dtype = entry.get('data_type')
                                            schema_lines.append(f"{canon}: {dtype}")
                            except Exception:
                                pass
                            break
                except Exception:
                    # ignore issues listing versions
                    pass

        # fallback to instance profile schema
        if not schema_lines and kind:
            profile_path = os.path.join('domain', 'catalog', 'datasets', kind, 'profile.json')
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, 'r') as pf:
                        prof = json.load(pf)
                        for col, info in prof.items():
                            dtype = info.get('observed_type') if isinstance(info, dict) else 'unknown'
                            schema_lines.append(f"{col}: {dtype}")
                except Exception:
                    pass

        schema_text = '\n'.join(schema_lines) if schema_lines else 'No schema available.'

        # Build filters description (textual only)
        if filters:
            filters_text = '\n'.join([f"{k}: {v}" for k, v in filters.items()])
        else:
            filters_text = 'No filters selected.'

        # Build a constrained prompt that explicitly provides the metrics list and strict rules
        # Build two prompt templates (generalist for direct SQL safety net, specialist for analytical intents) and choose by mode
        generalist_prompt = """GENERALIST SQL GENERATOR (Direct SQL / Safety Net)

CONTEXT:
KIND: {kind}
SCHEMA: {schema_text}
FILTERS: {filters_text}
METRICS: {metrics}
DIMENSIONS: {dimensions}
USER_QUESTION: {question}

INSTRUCTIONS (must follow exactly):
- You MUST use canonical snake_case column names only (from the SCHEMA section).
- The SELECT clause MUST only contain aggregations (e.g., SUM, AVG) of the columns from the "Metrics to Select" list.
- If "Dimensions to Group By" are provided, include them in SELECT and in a GROUP BY clause.
- Build a WHERE clause using all key-value pairs from FILTERS when provided. If none provided, omit the WHERE clause.
- All WHERE clause comparisons MUST be case-insensitive using LOWER(column) = LOWER('<value>').
- The query MUST end with LIMIT 1000.

OUTPUT:
Return EXACTLY one JSON object with key 'sql' and the SQL string as its value.

EXAMPLE:
{{"sql": "SELECT SUM(dollar_sales) AS dollar_sales, SUM(unit_sales) AS unit_sales, SUM(volume_sales) AS volume_sales FROM data WHERE LOWER(market)=LOWER('total us xaoc') AND LOWER(time_agg)=LOWER('latest 52 wks - w/e 08/16/25') LIMIT 1000"}}
"""

        specialist_prompt = """You are a SQL generator for analytical intents.

CONTEXT:
KIND: {kind}
SCHEMA: {schema_text}
FILTERS: {filters_text}
METRICS: {metrics}
DIMENSIONS: {dimensions}
USER_QUESTION: {question}

RULES (must follow):
1) Use ONLY canonical snake_case column names for all column references.
2) SELECT clause MUST only contain aggregations (e.g., SUM, AVG) of the columns from the METRICS list.
3) If Dimensions are provided, include them in SELECT and in a GROUP BY clause.
4) Do not perform joins. Single table only.
5) Do not use SELECT *. Explicitly list columns to return.
6) Build a WHERE clause using FILTERS when provided; comparisons must be case-insensitive using LOWER(column) = LOWER('<value>').
7) The query MUST end with LIMIT 1000.

OUTPUT:
Respond with EXACTLY one JSON object with key 'sql'."""

        # choose prompt based on mode
        mode = input_data.get('mode') or 'specialist'
        # ensure dimensions is available for formatting
        dimensions = input_data.get('dimensions') or input_data.get('dims') or []
        if isinstance(dimensions, list):
            dimensions_text = ', '.join(dimensions) if dimensions else ''
        else:
            dimensions_text = str(dimensions)
        if mode == 'generalist':
            prompt = generalist_prompt
        else:
            prompt = specialist_prompt

        # format the prompt with current values
        prompt = prompt.format(kind=kind, schema_text=schema_text, filters_text=filters_text, metrics=metrics, question=question, dimensions=dimensions_text)



    # Call the LLM with the assembled prompt in deterministic JSON mode
    try:
        # record the exact prompt used (redact secrets in prompt if present)
        sql_llm_prompt = prompt
        resp = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-5-mini",
            max_tokens=2048,
            temperature=0.0,
            api_key=api_key,
            api_base=api_base,
            # best-effort JSON mode flag for compatible providers
            response_format="json",
        )
    except Exception as e:
        # surface provider errors to caller in structured form
        return {"error": f"PROVIDER_ERROR: {e}", "sql_llm_prompt": sql_llm_prompt if 'sql_llm_prompt' in locals() else None, "sql_llm_output_raw": "(provider error)"}

    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    # Save raw model output for evidence
    sql_llm_output_raw = content

    # Try to parse JSON and return sql
    try:
        parsed = json.loads(content)
        sql_text = parsed.get('sql', '')
    except Exception:
        try:
            start = str(content).index('{')
            end = str(content).rindex('}') + 1
            parsed = json.loads(str(content)[start:end])
            sql_text = parsed.get('sql', '')
        except Exception:
            sql_text = ''

    # Preflight completeness: ensure candidate SQL contains SELECT ... FROM
    try:
        from insight_agent.sql_validator import is_sql_complete, normalize_sql, validate_sql, enforce_filters
        kind_local = locals().get('kind', '')
        # Run preflight completeness only when a kind is provided (we still want to validate even without kind in some tests)
        complete = is_sql_complete(sql_text)
        # If not complete and we are in specialist mode, keep a marker to allow fallback upstream
        mode_local = locals().get('mode', 'specialist')
        if not complete:
            # Build rails_status even on incomplete SQL so caller can record it
            rails_status = {
                'preflight_complete': False,
                'filters_enforced': False,
                'predicates_applied': 0,
                'validator_passed': False,
                'fallback_used': False,
                'failure_code': 'INCOMPLETE_SQL'
            }
            if mode_local == 'generalist':
                return {"error": "INCOMPLETE_SQL: your question did not specify what to calculate; try 'dollar sales by ...' or select a template.", "rails_status": rails_status, "sql_llm_prompt": sql_llm_prompt, "sql_llm_output_raw": sql_llm_output_raw}
            # signal upstream (agent) by returning a sentinel dict; agent will attempt fallback for specialist intents
            return {"error": "INCOMPLETE_SQL", "rails_status": rails_status, "sql_llm_prompt": sql_llm_prompt, "sql_llm_output_raw": sql_llm_output_raw}

        # Only apply normalization/filters/validation when the SQL is complete
        if kind_local and complete:
            sql_text = normalize_sql(sql_text, kind_local)
            # apply filters enforcement and compute predicate count
            sql_before = sql_text
            enforced_sql = enforce_filters(sql_text, filters or {})
            predicates_applied = 0
            if enforced_sql != sql_before:
                predicates_applied = enforced_sql.count('LOWER(')
            sql_text = enforced_sql
            try:
                validate_sql(sql_text, kind_local, filters or {})
                validator_passed = True
            except Exception:
                validator_passed = False
            rails_status = {
                'preflight_complete': True,
                'filters_enforced': (predicates_applied>0),
                'predicates_applied': predicates_applied,
                'validator_passed': validator_passed,
                'fallback_used': False,
                'failure_code': None if validator_passed else 'VALIDATION_FAILED'
            }
    except Exception as e:
        return {"error": str(e), "sql_llm_prompt": sql_llm_prompt, "sql_llm_output_raw": sql_llm_output_raw}

    return {"sql": sql_text, "rails_status": rails_status, "sql_llm_prompt": sql_llm_prompt, "sql_llm_output_raw": sql_llm_output_raw}


@tool
def data_synthesis_tool(input_text: str) -> str:
    """Synthesize a single-sentence summary from a dataframe head string or combined input.

    This tool accepts a single string (to be compatible with LangChain tool string inputs).
    """
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    model_name = "gpt-5-mini"

    if not api_key:
        return "Error: LITELLM_API_KEY is not set."

    # Treat the provided input_text as the dataframe head for now
    df_head = input_text
    cleaned_question = ""  # optional
    prompt = f"""Given the user's question, '{cleaned_question}', write a single, concise English sentence that summarizes the main finding in the data below.\n\n\nData:\n{df_head}\n"""

    try:
        resp = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model=model_name,
            max_tokens=4096,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        try:
            resp = litellm.completion(prompt, max_tokens=4096)
        except TypeError:
            resp = litellm.completion(prompt)

    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    if isinstance(content, dict):
        text = content.get('text', '') or content.get('content', '') or str(content)
        return text
    return str(content)


@tool
def intent_recognition_tool(user_question: str) -> str:
    """Classify the user's intent and extract simple entities.

    Returns a JSON string with keys: intent (string) and entities (object).
    Example: {"intent": "performance_summary", "entities": {"brand": "Jimmy Dean"}}
    """
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    if not api_key:
        return json.dumps({"error": "LITELLM_API_KEY not set"})

    valid_intents = IntentSchema.names() + ["direct_sql_query"]
    prompt = f"""You are a classifier. Analyze the user's question and return ONLY a JSON object with three keys:
- intent: one of the valid intent names exactly as listed below (including 'direct_sql_query' for simple SQL requests)
- entities: a JSON object mapping entity types to values (e.g., brand: "Jimmy Dean")
- dimensions: a JSON list of canonical column names (strings) to GROUP BY (may be empty)

Valid intents: {valid_intents}

User question:
{user_question}

If the question is a simple request that can be answered with a single SQL query, choose the intent 'direct_sql_query'. Also, extract any dimensions (canonical column names) that should be used for GROUP BY into the 'dimensions' list. Respond only with valid JSON, e.g. {{"intent": "direct_sql_query", "entities": {{}}, "dimensions": []}} (no explanatory text)."""

    try:
        resp = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-5-mini",
            max_tokens=512,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        try:
            resp = litellm.completion(prompt, max_tokens=512)
        except TypeError:
            resp = litellm.completion(prompt)

    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    try:
        parsed = json.loads(content)
        # ensure dimensions key exists
        if 'dimensions' not in parsed:
            parsed['dimensions'] = []
        return json.dumps(parsed)
    except Exception:
        try:
            start = str(content).index('{')
            end = str(content).rindex('}') + 1
            parsed = json.loads(str(content)[start:end])
            if 'dimensions' not in parsed:
                parsed['dimensions'] = []
            return json.dumps(parsed)
        except Exception:
            return json.dumps({"intent": "unknown", "entities": {}, "dimensions": []})


@tool
def metric_selection_tool(intent: str) -> list:
    """Select metrics based on the detected intent using the canonical IntentSchema mapping."""
    intent_map = {
        IntentSchema.sales_performance.value: ["dollar_sales", "unit_sales", "volume_sales"],
        IntentSchema.yoy_performance.value: ["dollar_sales", "dollar_sales_ya", "unit_sales", "unit_sales_ya", "volume_sales", "volume_sales_ya"],
        IntentSchema.distribution_summary.value: ["tdp_ty", "tdp_ya"],
        IntentSchema.pricing_summary.value: ["avg_volume_price", "avg_volume_price_ya"],
        IntentSchema.velocity_summary.value: ["velocity", "velocity_ya"],
        IntentSchema.promotion_summary.value: ["promo_dollar_sales", "promo_dollar_sales_ya"],
    }

    return intent_map.get(intent, [])
