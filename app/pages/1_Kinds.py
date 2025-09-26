import streamlit as st
from insight_agent.kind_manager import create_kind

st.title('Create a New Kind')

st.markdown('Upload the required mapping workbook and a sample data file to create a new Kind.')

mapping = st.file_uploader('Required Mapping Workbook', type=['xlsx', 'xls', 'csv'])
sample = st.file_uploader('Sample Data', type=['xlsx', 'xls', 'csv'])

kind_name = st.text_input('Kind Name')

if st.button('Create Kind'):
    if mapping is None:
        st.error('Please upload the Required Mapping Workbook before creating a Kind.')
    elif not kind_name or kind_name.strip() == '':
        st.error('Please enter a valid Kind Name.')
    else:
        success, message = create_kind(mapping, kind_name.strip())
        if success:
            st.success(message)
        else:
            st.error(message)
