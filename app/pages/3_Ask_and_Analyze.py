import streamlit as st
import os
import json

st.title('Ask & Analyze')

# initialize session state for SQL result
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = ''

# List available kinds
kinds_dir = os.path.join('domain','catalog','kinds')
kind_options = []
if os.path.exists(kinds_dir):
    for p in os.listdir(kinds_dir):
        if os.path.isdir(os.path.join(kinds_dir,p)):
            kind_options.append(p)

selected_kind = st.selectbox('Select a Kind', options=[''] + kind_options)

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

        for col, info in sorted(profile.items(), key=order_key):
            values = info['values'] if isinstance(info, dict) else info
            key = f"filter_{col}"
            val = st.selectbox(f"Filter by {col}", options=[''] + list(values), key=key)
            if val:
                selected_filters_ui[col] = val

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

    # Use new backend processor that returns evidence pieces
    from insight_agent.llm_client import process_question
    evidence = process_question(selected_kind, question, selected_filters)

    # Show SQL prompt and result summary
    st.markdown('**Generated SQL Prompt:**')
    st.code(evidence.get('sql_prompt',''))
    st.session_state.sql_query = ''

    # Display summary
    if evidence.get('summary_raw'):
        st.markdown('**Summary:**')
        st.markdown(evidence.get('summary_raw'))

    st.markdown('**Query Results:**')
    st.dataframe(evidence.get('dataframe', None))

    # Add Evidence expander (5 parts)
    with st.expander('Show Evidence'):
        # 1) Full prompt sent to SQL LLM
        with st.expander('1. SQL Prompt'):
            st.code(evidence.get('sql_prompt',''))

        # 2) Raw JSON response from SQL LLM
        with st.expander('2. SQL Raw Response'):
            st.code(evidence.get('sql_raw_response',''))

        # 3) Complete DataFrame result
        with st.expander('3. DataFrame Result'):
            df_full = evidence.get('dataframe')
            if df_full is not None:
                st.dataframe(df_full)
            else:
                st.write('No data')

        # 4) Full prompt sent to Summary LLM
        with st.expander('4. Summary Prompt'):
            st.code(evidence.get('summary_prompt',''))

        # 5) Raw text response from Summary LLM
        with st.expander('5. Summary Raw Response'):
            st.code(evidence.get('summary_raw',''))

# If a SQL query has been stored in session state, display it
if st.session_state.sql_query:
    st.markdown('**Generated SQL:**')
    st.code(st.session_state.sql_query)
