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
    """Build a prompt from the dataframe and user's question and return a one-sentence summary from litellm.

    This function queries LiteLLM for the model's context window and estimates tokens. If the
    prompt would exceed ~90% of the context window, it returns an informative message.
    Any API errors are caught and a graceful message returned.
    """
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    model_name = "gpt-5-mini"

    if not api_key:
        return "Error: LITELLM_API_KEY is not set."

    # Convert entire dataframe to string for the summary context
    try:
        df_text = df.to_string()
    except Exception:
        df_text = str(df)

    # Attempt to obtain context window / token limit from litellm
    context_limit = None
    try:
        model_info = getattr(litellm, 'model_info', None)
        if callable(model_info):
            info = model_info(model_name)
            # Common keys: 'context_window', 'context_size', 'max_tokens'
            context_limit = info.get('context_window') or info.get('context_size') or info.get('max_tokens')
    except Exception:
        context_limit = None

    # Estimate tokens in prompt (simple heuristic: 4 chars ~ 1 token)
    prompt_text = f"Question: {user_question}\n\nData:\n{df_text}"
    estimated_tokens = max(1, len(prompt_text) // 4)

    if context_limit is not None:
        try:
            if estimated_tokens > 0.9 * int(context_limit):
                return "The result is too large for an AI summary."
        except Exception:
            # if parsing fails, continue and attempt to summarize
            pass

    # Build the user-facing prompt
    prompt = (
        "You are a helpful assistant.\n"
        f"User question: {user_question}\n\n"
        "Here is the query result (entire result as text):\n"
        f"{df_text}\n\n"
        "Provide a concise, one-sentence summary that answers the user's question based on the data."
    )

    try:
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

        try:
            content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
        except Exception:
            content = resp

        if isinstance(content, dict):
            return content.get('text', '') or content.get('content', '') or str(content)
        return str(content)
    except Exception:
        return "AI summary is currently unavailable."
