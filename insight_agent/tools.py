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
        prompt = f"""You are a SQL generator. Your only job is to write a single SQL query (no joins) that answers the user's question using the provided METRICS list.

INPUTS (do not invent or use any other inputs):
KIND: {kind}
SCHEMA: {schema_text}
FILTERS: {filters_text}
METRICS: {metrics}
USER_QUESTION: {question}

RULES (CRITICAL):
1) Use ONLY the canonical_name for all column references. NEVER use original_name or description.
2) Use ONLY columns from the provided METRICS list for measures. Do NOT include other measure columns.
3) Do not perform joins. Single table only.
4) Do not use SELECT *. Explicitly list columns to return.
5) Ensure the query includes a LIMIT clause (e.g., LIMIT 10) unless an explicit limit is provided in the question.

OUTPUT:
Respond with EXACTLY one JSON object and nothing else. The object must have a single key 'sql' whose value is the SQL query string. Example: {{"sql": "SELECT dollar_sales FROM data WHERE brand='X' LIMIT 10"}}
"""


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

    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    # Try to parse JSON and return sql
    try:
        parsed = json.loads(content)
        return parsed.get('sql', '')
    except Exception:
        try:
            start = str(content).index('{')
            end = str(content).rindex('}') + 1
            parsed = json.loads(str(content)[start:end])
            return parsed.get('sql', '')
        except Exception:
            return ''

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
    prompt = f"""You are a classifier. Analyze the user's question and return ONLY a JSON object with two keys:
- intent: one of the valid intent names exactly as listed below (including 'direct_sql_query' for simple SQL requests)
- entities: a JSON object mapping entity types to values (e.g., brand: "Jimmy Dean")

Valid intents: {valid_intents}

User question:
{user_question}

If the question is a simple request that can be answered with a single SQL query, choose the intent 'direct_sql_query'. Otherwise, choose one of the specialist intents. Respond only with valid JSON, e.g. {{"intent": "direct_sql_query", "entities": {{}}}} (no explanatory text)."""

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
        return json.dumps(parsed)
    except Exception:
        try:
            start = str(content).index('{')
            end = str(content).rindex('}') + 1
            parsed = json.loads(str(content)[start:end])
            return json.dumps(parsed)
        except Exception:
            return json.dumps({"intent": "unknown", "entities": {}})


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
