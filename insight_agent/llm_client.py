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

    # Make a completion call. We set a short max_tokens to encourage concise output.
    resp = litellm.completion(
        prompt=prompt,
        model="openai/gpt-5-mini",
        max_tokens=256,
        api_key=api_key,
        api_base=api_base,
    )

    # Expecting resp to be a string containing JSON like: {"sql": "SELECT ..."}
    try:
        parsed = json.loads(resp)
        return parsed.get('sql', '')
    except Exception:
        # Try to extract JSON substring
        try:
            start = resp.index('{')
            end = resp.rindex('}') + 1
            parsed = json.loads(resp[start:end])
            return parsed.get('sql', '')
        except Exception:
            return ''
