import re


def are_inputs_complete(selected_kind, profile, session_state):
    """Return (complete:bool, missing:list).

    - selected_kind must be non-empty
    - profile: mapping of col -> info dict; a column is required when info.get('required') is truthy
    - session_state: an object supporting .get(key) (e.g., streamlit.session_state)
    """
    missing = []
    if not selected_kind:
        return False, ['kind']

    if not profile:
        return True, []

    for col, info in profile.items():
        if isinstance(info, dict) and info.get('required', False):
            safe_col = re.sub(r'[^0-9a-zA-Z_]', '_', str(col))
            key = f"filter_{safe_col}"
            if session_state.get(key) in (None, ''):
                missing.append(col)

    return (len(missing) == 0, missing)
