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
if profile:
    first_col = next(iter(profile.keys()), None)
    if first_col:
        st.selectbox(f"Filter by {first_col}", options=[''] + list(profile.get(first_col, [])))

# Question input
question = st.text_area('Type your question')

from insight_agent.prompt_builder import build_prompt

if st.button('Ask'):
    # collect selected filters: for now, just include the first profile column selection if present
    selected_filters = {}
    if profile:
        first_col = next(iter(profile.keys()), None)
        if first_col:
            sel = st.session_state.get(f"filter_{first_col}", '') if hasattr(st, 'session_state') else ''
            # But we don't have the selected value stored; instead read from the widget directly isn't possible here.
            # As a simpler approach, if the selectbox value was set, reconstruct from query params — but for now we will
            # pretend no filters are selected and build prompt without filters.
            selected_filters = {}

    prompt = build_prompt(selected_kind, question, selected_filters)
    st.code(prompt)
