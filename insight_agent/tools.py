from langchain.tools import tool
import os
import json
import litellm
from insight_agent.contracts import IntentSchema

from dotenv import load_dotenv
load_dotenv()


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

    # Normalize possible provider response shapes into 'content' variable
    content = None
    try:
        # resp may be an object with .choices[0].message.content
        if hasattr(resp, 'choices'):
            try:
                content = resp.choices[0].message.content
            except Exception:
                try:
                    content = resp.choices[0].text
                except Exception:
                    content = None
    except Exception:
        content = None

    # fallback: resp itself may be a string or dict-like
    if content is None:
        content = resp

    # Try to parse JSON and return sql
    sql_text = None
    # If content is a string, try json.loads
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'sql' in parsed:
                sql_text = parsed.get('sql')
        except Exception:
            # try to extract JSON object substring
            try:
                start = str(content).index('{')
                end = str(content).rindex('}') + 1
                parsed = json.loads(str(content)[start:end])
                if isinstance(parsed, dict) and 'sql' in parsed:
                    sql_text = parsed.get('sql')
            except Exception:
                sql_text = None

    # If content is a dict-like
    if sql_text is None and isinstance(content, dict):
        sql_text = content.get('sql')

    # If content is a provider object not caught above, try common paths
    if sql_text is None and hasattr(content, '__dict__'):
        d = getattr(content, '__dict__', {})
        # attempt common keys
        for key in ('sql', 'content', 'text'):
            if key in d and isinstance(d[key], str):
                # if it's JSON string, try parse
                try:
                    parsed = json.loads(d[key])
                    if isinstance(parsed, dict) and 'sql' in parsed:
                        sql_text = parsed.get('sql')
                        break
                except Exception:
                    sql_text = d[key]
                    break

    # Final safety: never return empty string. If no sql_text found, return an error description
    if not sql_text:
        return json.dumps({"error": "NO_SQL_RETURNED", "raw": str(content)})

    # Post-process SQL to enforce rails: canonicalization, symmetric LOWER, table whitelist, etc.
    try:
        from insight_agent.sql_validator import normalize_sql, validate_sql
        # skip validation if kind missing
        kind = kind if 'kind' in locals() else ''
        sql_text = normalize_sql(sql_text, kind) if kind else sql_text
        if kind:
            validate_sql(sql_text, kind)
    except Exception as e:
        # return structured error rather than an empty string
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
