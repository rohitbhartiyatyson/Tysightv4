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
        # Diagnostic: print parameters being sent to litellm.completion
        print(f"[llm_client][NL2SQL] calling litellm.completion with model=gpt-5-mini, api_base={api_base}, api_key_set={bool(api_key)}")
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


def get_summary_from_df(df, user_question: str) -> str:
    """Simplified summary helper: build a small prompt from the dataframe head and call the model.

    Any errors are caught and a user-friendly message returned.
    """
    try:
        print("[llm_client] get_summary_from_df: start")
        api_key = os.environ.get('LITELLM_API_KEY')
        api_base = os.environ.get('LITELLM_API_BASE')
        model_name = "claude-3-haiku-20240307"

        if not api_key:
            print("[llm_client] No API key set")
            return "Error: LITELLM_API_KEY is not set."

        try:
            df_head = df.head().to_string()
        except Exception:
            df_head = str(df)

        prompt = f'The user asked: "{user_question}". Based on this data, write a one-sentence summary of the answer. Data: {df_head}'
        print(f"[llm_client] prompt length={len(prompt)}")
        # Diagnostic: print the full prompt being sent
        print(f"[llm_client] prompt=
{prompt}
")

        try:
            resp = litellm.completion(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                max_tokens=150,
                api_key=api_key,
                api_base=api_base,
            )
        except TypeError:
            try:
                resp = litellm.completion(prompt, max_tokens=150)
            except TypeError:
                resp = litellm.completion(prompt)

        # Extract content
        try:
            content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
            print(f"[llm_client] raw content: {str(content)[:200]}")
        except Exception as exc:
            content = resp
            print(f"[llm_client] content extraction failed: {exc}")

        if isinstance(content, dict):
            text = content.get('text', '') or content.get('content', '') or str(content)
            return text
        return str(content)
    except Exception as e:
        print(f"[llm_client] get_summary_from_df error: {e}")
        # Detailed representation for debugging
        print(f"Detailed summary exception: {repr(e)}")
        return "Error: The AI summary could not be generated. Please try again later."
