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
                                            schema_lines.append(f"{k}: {v.get('data_type','unknown')}")
                                    else:
                                        # fallback when list
                                        for entry in mapping:
                                            oname = entry.get('original_name') or entry.get('canonical_name')
                                            dtype = entry.get('data_type')
                                            schema_lines.append(f"{oname}: {dtype}")
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

        # Build filters description
        if filters:
            filters_text = '\n'.join([f"{k} = {v}" for k, v in filters.items()])
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
- You MUST use the canonical_name for all columns.
- The SELECT clause MUST only contain aggregations (e.g., SUM, AVG) of the columns from the "Metrics to Select" list.
- If "Dimensions to Group By" are provided, include them in SELECT and in a GROUP BY clause.
- Build a WHERE clause using all key-value pairs from FILTERS when provided. If none provided, omit the WHERE clause.
- All WHERE clause comparisons MUST be case-insensitive using LOWER(column) = LOWER('value').
- The query MUST end with LIMIT 1000.

OUTPUT:
Return EXACTLY one JSON object with key 'sql' and the SQL string as its value. Example: {{"sql": "SELECT SUM(dollar_sales) AS dollar_sales, category FROM data WHERE LOWER(brand)=LOWER('X') GROUP BY category LIMIT 1000"}}
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
1) Use ONLY canonical_name for all column references.
2) SELECT clause MUST only contain aggregations (e.g., SUM, AVG) of the columns from the METRICS list.
3) If Dimensions are provided, include them in SELECT and in a GROUP BY clause.
4) Do not perform joins. Single table only.
5) Do not use SELECT *. Explicitly list columns to return.
6) Build a WHERE clause using FILTERS when provided; comparisons must be case-insensitive using LOWER().
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



    # Call the LLM with the assembled prompt
    try:
        resp = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-5-mini",
            max_tokens=1024,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        try:
            resp = litellm.completion(prompt, max_tokens=1024)
        except TypeError:
            resp = litellm.completion(prompt)

    # Normalize provider response into a 'content' variable
    content = None
    try:
        if hasattr(resp, 'choices'):
            # OpenAI-like response
            try:
                content = resp.choices[0].message.content
            except Exception:
                try:
                    content = resp.choices[0].text
                except Exception:
                    content = None
    except Exception:
        content = None

    if content is None:
        content = resp

    # Attempt to extract SQL from multiple shapes
    sql_text = None

    # 1) If content is a string: try json.loads -> dict['sql']
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'sql' in parsed:
                sql_text = parsed.get('sql')
        except Exception:
            # try to extract a JSON substring
            try:
                s = str(content)
                start = s.index('{')
                end = s.rindex('}') + 1
                parsed = json.loads(s[start:end])
                if isinstance(parsed, dict) and 'sql' in parsed:
                    sql_text = parsed.get('sql')
            except Exception:
                # fallback: content might already be raw SQL
                if 'SELECT' in content.upper():
                    sql_text = content

    # 2) If content is a dict-like
    if sql_text is None and isinstance(content, dict):
        if 'sql' in content and isinstance(content.get('sql'), str):
            sql_text = content.get('sql')
        else:
            # common nested paths
            for key in ('content', 'text', 'message'):
                val = content.get(key)
                if isinstance(val, str) and 'SELECT' in val.upper():
                    sql_text = val
                    break

    # 3) If content is an object, attempt common attributes
    if sql_text is None and hasattr(content, '__dict__'):
        d = getattr(content, '__dict__', {})
        # look for direct sql, content or text
        for key in ('sql', 'content', 'text'):
            v = d.get(key)
            if isinstance(v, str):
                # try parse JSON inside
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, dict) and 'sql' in parsed:
                        sql_text = parsed.get('sql')
                        break
                except Exception:
                    if 'SELECT' in v.upper():
                        sql_text = v
                        break

    # Never return an empty string; return structured error if no SQL found
    if not sql_text:
        return json.dumps({"error": "NO_SQL_RETURNED", "raw": str(content)})

    # Post-process SQL (only validate if kind provided)
    try:
        from insight_agent.sql_validator import normalize_sql, validate_sql
        kind_local = locals().get('kind', '')
        if kind_local:
            sql_text = normalize_sql(sql_text, kind_local)
            validate_sql(sql_text, kind_local)
    except Exception as e:
        return json.dumps({"error": "VALIDATION_FAILED", "message": str(e)})

    return sql_text

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
