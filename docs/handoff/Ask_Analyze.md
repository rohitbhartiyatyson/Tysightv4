# Ask & Analyze inputs

Short summary of the current behavior:

- No auto-selection of Kind or filters.
- Ask stays disabled until required inputs are chosen. A column is considered required when `profile[<col>]['required'] == True` in the Kind profile.
- Selections persist per Kind via `st.session_state['filters_by_kind'][<kind>]`, and are only written when the user actually picks a value (no overwrites on reruns).

