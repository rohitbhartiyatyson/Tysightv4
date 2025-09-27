import os
import json


def build_prompt(kind_name, user_question, selected_filters=None):
    """Build a human-readable prompt describing the dataset and the user's intent.

    Args:
        kind_name (str): name of the kind (directory under domain/catalog/kinds)
        user_question (str): the user's natural language question
        selected_filters (dict): mapping of column->value selections

    Returns:
        str: the constructed prompt
    """
    base = os.path.join('domain', 'catalog', 'kinds', kind_name, 'v1')
    mapping_path = os.path.join(base, 'mapping_effective.json')
    desc_path = os.path.join(base, 'description.md')

    mapping = []
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, 'r') as mf:
                mapping = json.load(mf)
        except Exception:
            mapping = []

    description = ''
    if os.path.exists(desc_path):
        try:
            with open(desc_path, 'r') as df:
                description = df.read()
        except Exception:
            description = ''

    # Build schema description from mapping using canonical_name and description
    schema_lines = []
    for rec in mapping:
        orig = rec.get('original_name', '')
        canon = rec.get('canonical_name', orig)
        desc = rec.get('description', '')
        schema_lines.append(f"- {canon} (source column: {orig}): {desc}")

    parts = []
    # Strict instruction to enforce JSON-only output
    instruction = (
        'You are a SQL generation bot. Your ONLY output must be a single JSON object with a key named "sql".'
        ' Do not add any other text, explanation, or markdown formatting.'
    )
    parts.append(instruction)

    # Helpful hint: tell the model the table name that will be used for execution
    parts.append("Your query will be executed against a table named 'data'. Please write queries starting with SELECT and referencing 'data' in the FROM clause.")
    parts.append(f"Dataset: {kind_name}")
    if description:
        parts.append("\nDescription:\n" + description)
    if schema_lines:
        parts.append("\nSchema:\n" + "\n".join(schema_lines))
    if selected_filters:
        filt_lines = [f"- {k}: {v}" for k, v in (selected_filters.items() if isinstance(selected_filters, dict) else [])]
        parts.append("\nSelected Filters:\n" + "\n".join(filt_lines))
    parts.append("\nQuestion:\n" + (user_question or ''))

    return "\n\n".join(parts)
