def onboard_instance(kind_name, instance_file):
    """Validate an instance file against the kind's effective mapping.

    Args:
        kind_name (str): The name of the kind to validate against.
        instance_file: file-like object for the instance data.

    Returns:
        tuple: (success: bool, message: str)
    """
    import os
    import pandas as pd
    import json

    base_dir = os.path.join('domain', 'catalog', 'kinds', kind_name, 'v1')
    effective_path = os.path.join(base_dir, 'mapping_effective.json')
    if not os.path.exists(effective_path):
        return False, f"Error: Effective mapping not found for kind '{kind_name}'."

    try:
        with open(effective_path, 'r') as ef:
            mapping = json.load(ef)
    except Exception as exc:
        return False, f"Error reading effective mapping: {exc}"

    try:
        name = getattr(instance_file, 'name', '')
        if isinstance(name, str) and name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(instance_file)
        else:
            try:
                instance_file.seek(0)
            except Exception:
                pass
            df = pd.read_csv(instance_file)
    except Exception as exc:
        return False, f"Error reading instance file: {exc}"

    # Extract expected columns from mapping
    expected = [rec.get('original_name') for rec in mapping if 'original_name' in rec]
    actual = list(df.columns)

    if set(expected) == set(actual):
        return True, "Instance is valid."
    else:
        missing = [c for c in expected if c not in actual]
        extra = [c for c in actual if c not in expected]
        return False, f"Error: Instance columns do not match. Missing: {missing}. Extra: {extra}."
