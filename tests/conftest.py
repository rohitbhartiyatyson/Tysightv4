import pytest

@pytest.fixture(autouse=True)
def patch_litellm(monkeypatch):
    """Auto-patch common litellm completion paths and set a dummy API key for tests.

    Tests which need custom behavior can still monkeypatch again inside the test.
    """
    monkeypatch.setenv('LITELLM_API_KEY', 'dummy')
    # default no-op completion to avoid accidental external calls; tests will override as needed
    def _noop(*args, **kwargs):
        return ''
    try:
        monkeypatch.setattr('insight_agent.tools.litellm.completion', _noop)
    except Exception:
        pass
    try:
        monkeypatch.setattr('insight_agent.llm_client.litellm.completion', _noop)
    except Exception:
        pass
