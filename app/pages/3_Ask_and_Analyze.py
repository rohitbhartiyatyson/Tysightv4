from pathlib import Path
import streamlit as st
import os
import json

st.title('Streamlit App Output')

st.title('Ask & Analyze')

# Setup a lightweight logger for debug entries when TEST_MODE=1 or session_state.debug
import logging
logger = logging.getLogger('ask_and_analyze')
if not logger.handlers:
    Path('logs').mkdir(exist_ok=True)
    handler = logging.FileHandler('logs/ask_and_analyze_debug.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

# initialize session state for SQL result and filters
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = ''
if 'filters_by_kind' not in st.session_state:
    st.session_state['filters_by_kind'] = {}

# List available kinds
kinds_dir = os.path.join('domain','catalog','kinds')
kind_options = []
if os.path.exists(kinds_dir):
    for p in os.listdir(kinds_dir):
        if os.path.isdir(os.path.join(kinds_dir,p)):
            kind_options.append(p)

# Use session_state key so we can react to kind changes predictably
# selected_kind should be empty on load; do not auto-select via TEST_MODE or fixtures
selected_kind = st.selectbox('Select a Kind', options=[''] + kind_options, index=0, key='selected_kind')

# ensure selected_kind variable reflects session state (default empty string)
selected_kind = st.session_state.get('selected_kind', '')

profile = {}
if selected_kind:
    # Load profile.json from the datasets directory for the selected kind
    datasets_dir = os.path.join('domain','catalog','datasets')
    profile_path = os.path.join(datasets_dir, selected_kind, 'profile.json')
    if os.path.exists(profile_path):
        try:
            with open(profile_path,'r') as pf:
                profile = json.load(pf)
        except Exception:
            profile = {}

    # For all filterable columns in profile_data, show their unique values and capture selections
    selected_filters_ui = {}
    if profile:
        # Sort filters by filter_display_order when present (None treated as large)
        def order_key(item):
            col, info = item
            order = info.get('filter_display_order') if isinstance(info, dict) else None
            return (order is None, order if order is not None else 999999)

        # Determine if any filters are defined (presence of filter_display_order on any column)
        filters_defined = any(
            (isinstance(info, dict) and info.get('filter_display_order') is not None)
            for _, info in profile.items()
        )

        if not filters_defined:
            st.info("No filters are defined for this Kind. You can define them in your mapping file using the filter_display_order column.")

        for col, info in sorted(profile.items(), key=order_key):
            values = info['values'] if isinstance(info, dict) else info
            values_list = list(values) if values is not None else []
            # build a stable widget key per column (do NOT include kind in key to avoid leaking across page reloads)
            # sanitize column name to letters/numbers/underscore
            import re
            safe_col = re.sub(r'[^0-9a-zA-Z_]', '_', str(col))
            key = f"filter_{safe_col}"

            # ensure filters_by_kind mapping exists for this kind
            if selected_kind not in st.session_state['filters_by_kind']:
                st.session_state['filters_by_kind'][selected_kind] = {}

            # Remove initializer guard and auto-defaulting. We do not write defaults for filter widgets.
            # Keep keys stable. If the session_state has an existing value, keep it; otherwise leave it absent/None.
            current_val = st.session_state.get(key, None)

            # Remove any per-kind init flags if present
            last_init_key = f"_init_{selected_kind}_{col}"
            if last_init_key in st.session_state:
                try:
                    del st.session_state[last_init_key]
                except Exception:
                    pass

            # Do not auto-set defaults. Keep existing session_state value if present; otherwise leave None/empty.
            # Logging: only output debug info when TEST_MODE=1 or explicit debug in session_state.
            try:
                import logging
                logger = logging.getLogger('ask_and_analyze')
                if os.environ.get('TEST_MODE')=='1' or st.session_state.get('debug'):
                    logger.debug(f"{key} options_count={len(values_list)} before={current_val} forced_default=False")
            except Exception:
                pass

            # Render widget (multiselect if indicated) tied to session_state key so the selected value is persistent
            is_multi = isinstance(info, dict) and info.get('multiselect', False)
            if is_multi:
                # ensure state is a list if the user selected something; otherwise leave unset
                current = st.session_state.get(key, None)
                if current is not None and not isinstance(current, list):
                    st.session_state[key] = [current]
                val = st.multiselect(f"Filter by {col}", options=values_list, key=key)
            else:
                # for non-multi, do not coerce or set a default; keep existing value if present
                val = st.selectbox(f"Filter by {col}", options=[''] + values_list, index=0 if st.session_state.get(key) in (None,'') else values_list.index(st.session_state.get(key)), key=key) if values_list else st.selectbox(f"Filter by {col}", options=[''], key=key)

            # keep the filters_by_kind mirror up to date but only write when the user actually picked a value
            st.session_state['filters_by_kind'].setdefault(selected_kind, {})
            picked = st.session_state.get(key)
            if picked not in (None, ''):
                st.session_state['filters_by_kind'][selected_kind][col] = picked

            if st.session_state.get(key) not in (None, ''):
                selected_filters_ui[col] = st.session_state.get(key)

# Question input
question = st.text_area('Type your question')

from insight_agent.prompt_builder import build_prompt

# Guard the Ask button: require a Kind and at least one required filter selected.
# Determine required filters: those with filter_display_order present are considered filterable; but we only require filters explicitly marked 'required'=True in the profile.
required_missing = False
required_list = []
if selected_kind and profile:
    for c,inf in profile.items():
        if isinstance(inf, dict) and inf.get('required', False):
            required_list.append(c)
            keyc = f"filter_{''.join([ch if (ch.isalnum() or ch=='_') else '_' for ch in str(c)])}"
            if st.session_state.get(keyc) in (None, ''):
                required_missing = True

if not selected_kind:
    st.warning('Select Kind and filters first.')

if required_missing:
    st.warning('Select Kind and filters first.')

ask_enabled = selected_kind and not required_missing
if not st.button('Ask', disabled=not ask_enabled):
    pass
else:
    # collect selected filters from all filter widgets
    selected_filters = selected_filters_ui if isinstance(selected_filters_ui, dict) else {}

    # Debug logging: selected kind, user question, and filters
    # Use logger instead of prints; only write when TEST_MODE or explicit debug
    try:
        if os.environ.get('TEST_MODE')=='1' or st.session_state.get('debug'):
            logger.debug(f"[ui] selected_kind={selected_kind} selected_filters={selected_filters}")
    except Exception:
        pass

    # Build or get the LangChain agent executor and call it with the user's question
    from insight_agent.agent import build_agent

    try:
        executor = build_agent()
        # enable verbose tracing on the executor when possible
        try:
            setattr(executor, 'verbose', True)
        except Exception:
            pass
        # pass selected_kind into the agent input so it can locate the correct dataset
        agent_response = executor.invoke({"input": question, "kind": selected_kind})
        # print full agent response for debugging (includes intermediate_steps)
        try:
            if os.environ.get('TEST_MODE')=='1' or st.session_state.get('debug'):
                logger.debug(f"[agent_response] {str(agent_response)[:1000]}")
        except Exception:
            pass
    except Exception as e:
        st.error(f"Agent execution failed: {e}")
        agent_response = {"error": str(e)}

    # Determine final answer text
    final_answer = None
    if isinstance(agent_response, dict):
        final_answer = agent_response.get('output') or agent_response.get('final_answer') or agent_response.get('result') or agent_response.get('text') or json.dumps(agent_response)
    else:
        final_answer = str(agent_response)

    # Display summary
    st.markdown('**Summary:**')
    # Render the final answer as markdown to preserve wrapping and formatting
    try:
        st.markdown(final_answer)
    except Exception:
        st.write(final_answer)

    # Display agent evidence (chain of thought / intermediate steps)
    with st.expander('Show Evidence'):
        st.markdown('**Full Agent Response (raw):**')
        try:
            st.json(agent_response)
        except Exception:
            st.write(agent_response)

        # If the executor returned structured intermediate steps, display them nicely
        if isinstance(agent_response, dict):
            intermediates = agent_response.get('intermediate_steps') or agent_response.get('intermediates') or []
            if intermediates:
                st.markdown('**Intermediate Steps:**')
                for i, step in enumerate(intermediates):
                    # Each step may be a tuple (AgentAction, observation) when returned; render safely
                    try:
                        action, observation = step
                        st.write(f"Step {i+1} - Action: {getattr(action, 'tool', str(action))}")
                        st.write(f"Input: {getattr(action, 'tool_input', str(action))}")
                        st.write(f"Observation: {observation}")
                        st.write('---')
                    except Exception:
                        st.write(step)

# If a SQL query has been stored in session state, display it
if st.session_state.sql_query:
    st.markdown('**Generated SQL:**')
    st.code(st.session_state.sql_query)
