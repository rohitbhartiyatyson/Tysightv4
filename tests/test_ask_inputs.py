import types
from app.utils.ask_inputs import are_inputs_complete


class FakeSession(types.SimpleNamespace):
    def get(self, k, default=None):
        return getattr(self, k, default)


def test_empty_kind_disabled():
    sess = FakeSession()
    complete, missing = are_inputs_complete('', {}, sess)
    assert complete is False
    assert 'kind' in missing


def test_kind_but_missing_required_filter_disabled():
    sess = FakeSession()
    # profile says 'brand' is required
    profile = {'brand': {'required': True, 'values': ['A','B']}}
    # session has no filter_brand
    complete, missing = are_inputs_complete('Walmart POS', profile, sess)
    assert complete is False
    assert 'brand' in missing


def test_kind_and_required_filled_enabled():
    sess = FakeSession()
    setattr(sess, 'filter_brand', 'A')
    profile = {'brand': {'required': True, 'values': ['A','B']}}
    complete, missing = are_inputs_complete('Walmart POS', profile, sess)
    assert complete is True
    assert missing == []
