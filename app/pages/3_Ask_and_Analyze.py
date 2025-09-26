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
    profile_path = os.path.join(kinds_dir, selected_kind, 'v1', 'profile.json')
    if os.path.exists(profile_path):
        try:
            with open(profile_path,'r') as pf:
                profile = json.load(pf)
        except Exception:
            profile = {}

# Debug: show raw profile data
profile_data = profile
if profile_data:
    st.markdown('**Raw profile.json content:**')
    st.json(profile_data)

# For all filterable columns in profile_data, show their unique values and capture selections
selected_filters_ui = {}
if profile_data:
    for col, values in profile_data.items():
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

    prompt = build_prompt(selected_kind, question, selected_filters)
    st.code(prompt)

    # Now call the LLM client to get SQL
    from insight_agent.llm_client import get_sql_from_prompt
    sql = get_sql_from_prompt(prompt)
    # save SQL to session state for persistent display
    st.session_state.sql_query = sql

# If a SQL query has been stored in session state, display it
if st.session_state.sql_query:
    st.markdown('**Generated SQL:**')
    st.code(st.session_state.sql_query)
