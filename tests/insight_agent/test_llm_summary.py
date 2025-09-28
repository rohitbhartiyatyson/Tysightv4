import pytest
import pandas as pd
from unittest.mock import patch
from insight_agent.llm_client import get_summary_from_df


def test_get_summary_from_df_mock(monkeypatch):
    df = pd.DataFrame({'a':[1,2], 'b':['x','y']})

    class MockResp:
        def __init__(self, text):
            self.choices = [type('C', (), {'message': type('M', (), {'content': text})})]

    def fake_completion(*args, **kwargs):
        return MockResp('This is a one-sentence summary.')

    monkeypatch.setattr('litellm.completion', fake_completion)

    res = get_summary_from_df(df, 'What is the top-level insight?')
    assert 'one-sentence summary' in res or 'This is a one-sentence summary.' in res
