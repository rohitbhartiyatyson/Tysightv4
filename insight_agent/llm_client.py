import os
from dotenv import load_dotenv
import json
import litellm

# load .env into environment
load_dotenv()


def get_sql_from_prompt(prompt: str) -> str:
    """Call litellm to transform a prompt into a SQL query.

    The model is instructed to reply with strict JSON: {"sql": "..."}
    """
    # Read API config from environment
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')

    # If API key is missing, return a helpful error string instead of calling external API
    if not api_key:
        return "Error: LITELLM_API_KEY is not set. Please create a .env file with your API key."

    # Make a completion call. Use chat-style messages list expected by this LiteLLM instance.
    try:
        # Preferred call signature: litellm.completion(messages=[...], model=..., ...)
        resp = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-5-mini",
            max_tokens=1024,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        # Fallback for older or mocked litellm implementations that accept (prompt, max_tokens)
        try:
            resp = litellm.completion(prompt, max_tokens=1024)
        except TypeError:
            # Last resort: call with only prompt
            resp = litellm.completion(prompt)

    # The response may be a ModelResponse object from litellm. Extract the assistant
    # message content if present and parse it as JSON to obtain the SQL.
    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    try:
        parsed = json.loads(content)
        return parsed.get('sql', '')
    except Exception:
        # Try to extract JSON substring from the content
        try:
            start = content.index('{')
            end = content.rindex('}') + 1
            parsed = json.loads(content[start:end])
            return parsed.get('sql', '')
        except Exception:
            return ''


# New: get a brief one-sentence summary from a dataframe using the LLM
def get_summary_from_df(df, user_question: str) -> str:
    """Build a prompt from the dataframe and user's question and return a one-sentence summary from litellm."""
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')

    if not api_key:
        return "Error: LITELLM_API_KEY is not set."

    sample = ''
    try:
        sample = df.head().to_string()
    except Exception:
        sample = str(df)[:1000]

    prompt = (
        "You are a helpful assistant.\n"
        f"User question: {user_question}\n\n"
        "Here is a sample of the query result (first few rows):\n"
        f"{sample}\n\n"
        "Provide a concise, one-sentence summary that answers the user's question based on the data."
    )

    try:
        resp = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-5-mini",
            max_tokens=150,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        try:
            resp = litellm.completion(prompt, max_tokens=150)
        except TypeError:
            resp = litellm.completion(prompt)

    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    # If content is an object, try to extract string
    if isinstance(content, dict):
        return content.get('text', '') or content.get('content', '') or str(content)

    return str(content)
