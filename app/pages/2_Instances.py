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

if st.button('Onboard Instance'):
    st.info('Onboard Instance functionality is not implemented yet.')
