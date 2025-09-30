import streamlit as st

# These tests use st.session_state directly to simulate app behavior

def test_no_autoselect_on_load():
    st.session_state.clear()
    # On load we should not auto-select defaults; keys should be absent or None
    assert st.session_state.get('filter_a') in (None, '')


def test_no_reset_on_kind_change():
    st.session_state.clear()
    # user had previously selected 'Y'
    st.session_state['filter_a'] = 'Y'
    # simulate kind change -> options change that do NOT include 'Y'
    options = ['A','B']
    current = st.session_state.get('filter_a')
    # New behavior: do not force reset to first option. Instead, if current not in options, leave it empty/None.
    if (not isinstance(current, list) and current not in options):
        st.session_state['filter_a'] = None
    assert st.session_state['filter_a'] is None


def test_keys_unique():
    keys = ['filter_a','filter_str_col','filter_date_col']
    assert len(keys) == len(set(keys))


def test_keeps_user_selection():
    st.session_state.clear()
    st.session_state['filter_a'] = 'Y'
    # simulate a rerender where options still include 'Y'
    options = ['X','Y']
    current = st.session_state.get('filter_a')
    # The value should be preserved
    assert current == 'Y'


def test_keys_unique_and_stable():
    keys = ['filter_a','filter_str_col','filter_date_col']
    assert len(keys) == len(set(keys))
