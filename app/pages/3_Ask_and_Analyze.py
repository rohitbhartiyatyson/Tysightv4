import streamlit as st
import os
import json

st.title('Streamlit App Output')

st.title('Ask & Analyze')

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
selected_kind = st.selectbox('Select a Kind', options=[''] + kind_options, index=0, key='selected_kind')

# ensure selected_kind variable reflects session state
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
            # include the selected_kind in the key so changing kinds creates fresh widgets
            key = f"filter_{selected_kind}_{col}"

            # initialize session_state for this widget to the first value when kind first seen
            if selected_kind not in st.session_state['filters_by_kind']:
                st.session_state['filters_by_kind'][selected_kind] = {}
            if key not in st.session_state:
                default_val = values_list[0] if values_list else ''
                st.session_state[key] = default_val
                st.session_state['filters_by_kind'][selected_kind][col] = default_val

            # Render selectbox tied to session_state key so the selected value is persistent
            val = st.selectbox(f"Filter by {col}", options=values_list, key=key)
            # keep the filters_by_kind mirror up to date
            st.session_state['filters_by_kind'].setdefault(selected_kind, {})
            st.session_state['filters_by_kind'][selected_kind][col] = st.session_state.get(key)

            if st.session_state.get(key):
                selected_filters_ui[col] = st.session_state.get(key)

# Question input
question = st.text_area('Type your question')

from insight_agent.prompt_builder import build_prompt

if st.button('Ask'):
    # collect selected filters from all filter widgets
    selected_filters = selected_filters_ui if isinstance(selected_filters_ui, dict) else {}

    # Debug logging: selected kind, user question, and filters
    print(f"[ui] selected_kind={selected_kind}")
    print(f"[ui] user_question={question}")
    print(f"[ui] selected_filters={selected_filters}")

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
        print("[agent_response]", agent_response)
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
