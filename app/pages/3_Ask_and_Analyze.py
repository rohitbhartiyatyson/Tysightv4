import streamlit as st
import os
import json

st.title('Ask & Analyze')

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

# For the first filterable column in profile, show its unique values
filter_value = ''
first_col = None
if profile:
    first_col = next(iter(profile.keys()), None)
    if first_col:
        # capture the selected value so it can be used in the prompt
        filter_value = st.selectbox(f"Filter by {first_col}", options=[''] + list(profile.get(first_col, [])), key=f"filter_{first_col}")

# Question input
question = st.text_area('Type your question')

from insight_agent.prompt_builder import build_prompt

if st.button('Ask'):
    # collect selected filters: include the first profile column selection if present
    selected_filters = {}
    if profile and first_col:
        if filter_value:
            selected_filters[first_col] = filter_value

    prompt = build_prompt(selected_kind, question, selected_filters)
    st.code(prompt)

    # Now call the LLM client to get SQL
    from insight_agent.llm_client import get_sql_from_prompt
    sql = get_sql_from_prompt(prompt)
    st.code(sql)
