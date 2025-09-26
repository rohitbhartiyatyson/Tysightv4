import streamlit as st
import os

st.title('Onboard a New Instance')

# Find existing kinds
kinds_dir = os.path.join('domain', 'catalog', 'kinds')
kinds = []
if os.path.exists(kinds_dir):
    try:
        kinds = [d for d in os.listdir(kinds_dir) if os.path.isdir(os.path.join(kinds_dir, d))]
    except Exception:
        kinds = []

selected_kind = st.selectbox('Select a Kind to onboard', options=kinds if kinds else ['No kinds available'])

data_file = st.file_uploader('Upload instance data file', type=['csv', 'xlsx', 'xls'])

from insight_agent.instance_manager import onboard_instance

if st.button('Onboard Instance'):
    if selected_kind == 'No kinds available':
        st.error('No Kind available to onboard against.')
    elif data_file is None:
        st.error('Please upload an instance data file.')
    else:
        success, message = onboard_instance(selected_kind, data_file)
        if success:
            st.success(message)
        else:
            st.error(message)
