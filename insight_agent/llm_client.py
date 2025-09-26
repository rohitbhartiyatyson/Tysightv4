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
    resp = litellm.completion(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-5-mini",
        max_tokens=1024,
        api_key=api_key,
        api_base=api_base,
    )

    # Debug: print raw response for troubleshooting
    print(f"RAW LLM RESPONSE: {resp}")

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
