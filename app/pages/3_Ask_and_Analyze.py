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

if st.button('Ask'):
    st.info('Ask button pressed — functionality not implemented yet.')
