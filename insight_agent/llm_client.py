import json
import litellm


def get_sql_from_prompt(prompt: str) -> str:
    """Call litellm to transform a prompt into a SQL query.

    The model is instructed to reply with strict JSON: {"sql": "..."}
    """
    # Make a completion call. We set a short max_tokens to encourage concise output.
    resp = litellm.completion(prompt=prompt, model="gpt-3.5-turbo", max_tokens=256)

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
