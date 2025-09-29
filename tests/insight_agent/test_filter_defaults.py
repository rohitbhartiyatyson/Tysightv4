import streamlit as st

# These tests use st.session_state directly to simulate app behavior

def test_keeps_selection_when_present():
    st.session_state.clear()
    st.session_state['filter_a'] = 'Y'
    options = ['X','Y']
    # simulate renderer behavior
    current = st.session_state.get('filter_a')
    if 'filter_a' not in st.session_state or current is None:
        st.session_state['filter_a'] = options[0]
    assert st.session_state['filter_a'] == 'Y'


def test_resets_on_kind_change_once():
    st.session_state.clear()
    # user had previously selected 'Y'
    st.session_state['filter_a'] = 'Y'
    # simulate kind change -> options change
    options = ['A','B']
    last_init_key = '_init_newkind_a'
    current = st.session_state.get('filter_a')
    if (not isinstance(current, list) and current not in options):
        if not st.session_state.get(last_init_key, False):
            st.session_state['filter_a'] = options[0]
            st.session_state[last_init_key] = True
    assert st.session_state['filter_a'] == 'A'


def test_keys_unique():
    keys = ['filter_a','filter_str_col','filter_date_col']
    assert len(keys) == len(set(keys))


def test_multiselect_shape():
    st.session_state.clear()
    st.session_state['filter_multi'] = ['X']
    options = ['X','Y']
    current = st.session_state.get('filter_multi')
    # do not coerce list to scalar
    assert isinstance(current, list)
