import streamlit as st

st.title('Create a New Kind')

st.markdown('Upload the required mapping workbook and a sample data file to create a new Kind.')

mapping = st.file_uploader('Required Mapping Workbook', type=['xlsx', 'xls', 'csv'])
sample = st.file_uploader('Sample Data', type=['xlsx', 'xls', 'csv'])

st.button('Create Kind')
