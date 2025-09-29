from langchain.tools import tool
import os
import json
import litellm

from dotenv import load_dotenv
load_dotenv()


@tool
def sql_generation_tool(input_data) -> str:
    """Generate SQL given a structured input dict containing:
    {
        "question": str,
        "kind": str,
        "filters": dict,
        "metrics": list  (optional)
    }

    This tool will load the kind schema where possible and build a comprehensive
    prompt including schema, filters, metrics and the user's question before
    calling the LLM. For backward compatibility, if a string is passed it will
    be treated as the prompt body directly.
    """
    api_key = os.environ.get('LITELLM_API_KEY')
    api_base = os.environ.get('LITELLM_API_BASE')
    if not api_key:
        return "Error: LITELLM_API_KEY is not set. Please create a .env file with your API key."

    # Accept raw prompt strings for backward compatibility
    if isinstance(input_data, str):
        prompt = input_data
    else:
        # expected a dict-like input
        question = input_data.get('question') or input_data.get('input') or ''
        kind = input_data.get('kind') or ''
        filters = input_data.get('filters') or input_data.get('selected_filters') or {}
        metrics = input_data.get('metrics') or []

        # Try to load a schema from domain/catalog/kinds/<kind>/v*/mapping_effective.json
        schema_lines = []
        if kind:
            kinds_base = os.path.join('domain', 'catalog', 'kinds')
            kind_dir = os.path.join(kinds_base, kind)
            if os.path.exists(kind_dir):
                # pick the latest v* folder if present
                try:
                    versions = [d for d in os.listdir(kind_dir) if os.path.isdir(os.path.join(kind_dir, d))]
                    versions = sorted(versions)
                    for v in reversed(versions):
                        eff = os.path.join(kind_dir, v, 'mapping_effective.json')
                        if os.path.exists(eff):
                            try:
                                with open(eff, 'r') as fh:
                                    mapping = json.load(fh)
                                    # mapping_effective.json expected to be a list or dict of mappings
                                    if isinstance(mapping, dict):
                                        for k, v in mapping.items():
                                            schema_lines.append(f"{k}: {v.get('data_type','unknown')}")
                                    else:
                                        # fallback when list
                                        for entry in mapping:
                                            oname = entry.get('original_name') or entry.get('canonical_name')
                                            dtype = entry.get('data_type')
                                            schema_lines.append(f"{oname}: {dtype}")
                            except Exception:
                                pass
                            break

        # fallback to instance profile schema
        if not schema_lines and kind:
            profile_path = os.path.join('domain', 'catalog', 'datasets', kind, 'profile.json')
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, 'r') as pf:
                        prof = json.load(pf)
                        for col, info in prof.items():
                            dtype = info.get('observed_type') if isinstance(info, dict) else 'unknown'
                            schema_lines.append(f"{col}: {dtype}")
                except Exception:
                    pass

        schema_text = '\n'.join(schema_lines) if schema_lines else 'No schema available.'

        # Build filters description
        if filters:
            filters_text = '\n'.join([f"{k} = {v}" for k, v in filters.items()])
        else:
            filters_text = 'No filters selected.'

        prompt = f"""You are a SQL generator. Build a single SQL query (no joins) that answers the user's question.
Include only mapped & present columns. Enforce LIMIT and no SELECT *.

Kind: {kind}
Schema:
{schema_text}

Selected Filters:
{filters_text}

Metrics: {metrics}

User question:
{question}

Respond with a JSON object like: {{"sql": "SELECT ... LIMIT 10"}}
"""

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

    try:
        content = resp.choices[0].message.content if hasattr(resp, 'choices') else resp
    except Exception:
        content = resp

    # Try to parse JSON and return sql
    try:
        parsed = json.loads(content)
        return parsed.get('sql', '')
    except Exception:
        try:
            start = str(content).index('{')
            end = str(content).rindex('}') + 1
            parsed = json.loads(str(content)[start:end])
            return parsed.get('sql', '')
        except Exception:
            return ''