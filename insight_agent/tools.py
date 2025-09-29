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
