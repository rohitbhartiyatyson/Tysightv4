from langchain.tools import tool
import os
import json
import litellm

from dotenv import load_dotenv
load_dotenv()


@tool
def sql_generation_tool(prompt: str) -> str:
    """Generate SQL from a prompt using LiteLLM. Returns the SQL string or empty string on failure."""
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    if not api_key:
        return "Error: LITELLM_API_KEY is not set. Please create a .env file with your API key."

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

    try:
        parsed = json.loads(content)
        return parsed.get('sql', '')
    except Exception:
        try:
            start = content.index('{')
            end = content.rindex('}') + 1
            parsed = json.loads(content[start:end])
            return parsed.get('sql', '')
        except Exception:
            return ''


@tool
def data_synthesis_tool(df_head: str, user_question: str) -> str:
    """Synthesize a single-sentence summary from a dataframe head string and a user question."""
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    model_name = "gpt-5-mini"

    if not api_key:
        return "Error: LITELLM_API_KEY is not set."

    cleaned_question = user_question.splitlines()[-1].strip() if isinstance(user_question, str) else str(user_question)
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

    prompt = f"""You are a classifier. Analyze the user's question and return ONLY a JSON object with two keys:\n- intent: a short intent string such as \"performance_summary\" or \"compare_brands\"\n- entities: a JSON object mapping entity types to values (e.g., brand: \"Jimmy Dean\")\n\nUser question:\n{user_question}\n\nRespond only with valid JSON (no explanatory text)."""

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

    # Ensure the output is a JSON string
    try:
        parsed = json.loads(content)
        return json.dumps(parsed)
    except Exception:
        # Try to extract JSON substring
        try:
            start = content.index('{')
            end = content.rindex('}') + 1
            parsed = json.loads(content[start:end])
            return json.dumps(parsed)
        except Exception:
            return json.dumps({"intent": "unknown", "entities": {}})


@tool
def metric_selection_tool(intent: str) -> list:
    """Select metrics based on the detected intent. Pure code logic (no LLM call)."""
    if intent == "performance_summary":
        return ['dollar_sales', 'dollar_sales_ya', 'unit_sales', 'unit_sales_ya']
    # default fallback
    return []
