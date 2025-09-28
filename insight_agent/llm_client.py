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
        api_key = os.environ.get('LITELLM_API_KEY')
        api_base = os.environ.get('LITELLM_API_BASE')
        model_name = "gpt-5-mini"

        if not api_key:
            return "Error: LITELLM_API_KEY is not set."

        try:
            df_head = df.head().to_string()
        except Exception:
            df_head = str(df)

        # Sanitize the incoming user_question: take only the last line provided
        cleaned_question = user_question.splitlines()[-1].strip() if isinstance(user_question, str) else str(user_question)
        # Simplified prompt to avoid carrying over NL->SQL instructions
        df_head_str = df_head
        prompt = f"""Given the user's question, '{cleaned_question}', write a single, concise English sentence that summarizes the main finding in the data below.


Data:
{df_head_str}
"""
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

        # Extract content
        try:
            content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
        except Exception as exc:
            content = resp

        if isinstance(content, dict):
            text = content.get('text', '') or content.get('content', '') or str(content)
            return text
        return str(content)
    except Exception as e:
        return "Error: The AI summary could not be generated. Please try again later."


def process_question(kind_name: str, user_question: str, selected_filters: dict) -> dict:
    """Process a user question end-to-end and return evidence parts:
    - sql_prompt: prompt sent to SQL LLM
    - sql_raw_response: raw text response from SQL LLM
    - dataframe: pandas DataFrame result of SQL
    - summary_prompt: prompt sent to summary LLM
    - summary_raw: raw text response from summary LLM
    """
    # local imports to avoid top-level cycles
    from insight_agent.prompt_builder import build_prompt
    from insight_agent.query_executor import execute_query
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    # Build SQL prompt
    sql_prompt = build_prompt(kind_name, user_question, selected_filters)

    # Call SQL LLM
    try:
        resp_sql = litellm.completion(
            messages=[{"role": "user", "content": sql_prompt}],
            model="gpt-5-mini",
            max_tokens=1024,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        try:
            resp_sql = litellm.completion(sql_prompt, max_tokens=1024)
        except TypeError:
            resp_sql = litellm.completion(sql_prompt)

    try:
        sql_raw = resp_sql.choices[0].message.content if hasattr(resp_sql, 'choices') else resp_sql
    except Exception:
        sql_raw = resp_sql

    # Try to extract SQL string from raw
    sql_text = ''
    try:
        parsed = json.loads(sql_raw)
        sql_text = parsed.get('sql','')
    except Exception:
        # fallback: try to find JSON substring
        try:
            start = sql_raw.index('{')
            end = sql_raw.rindex('}')+1
            parsed = json.loads(sql_raw[start:end])
            sql_text = parsed.get('sql','')
        except Exception:
            sql_text = str(sql_raw)

    # Execute SQL to get dataframe
    df = None
    try:
        df = execute_query(kind_name, sql_text)
    except Exception:
        # if execution fails, keep df as empty dataframe
        import pandas as pd
        df = pd.DataFrame()

    # Build summary prompt and call summary LLM
    try:
        df_head = df.head().to_string()
    except Exception:
        df_head = str(df)
    cleaned_question = user_question.splitlines()[-1].strip() if isinstance(user_question, str) else str(user_question)
    summary_prompt = f"""Given the user's question, '{cleaned_question}', write a single, concise English sentence that summarizes the main finding in the data below.


Data:
{df_head}
"""

    try:
        resp_sum = litellm.completion(
            messages=[{"role": "user", "content": summary_prompt}],
            model="gpt-5-mini",
            max_tokens=4096,
            api_key=api_key,
            api_base=api_base,
        )
    except TypeError:
        try:
            resp_sum = litellm.completion(summary_prompt, max_tokens=4096)
        except TypeError:
            resp_sum = litellm.completion(summary_prompt)

    try:
        summary_raw = resp_sum.choices[0].message.content if hasattr(resp_sum, 'choices') else resp_sum
    except Exception:
        summary_raw = resp_sum

    return {
        'sql_prompt': sql_prompt,
        'sql_raw_response': str(sql_raw),
        'dataframe': df,
        'summary_prompt': summary_prompt,
        'summary_raw': str(summary_raw),
    }
