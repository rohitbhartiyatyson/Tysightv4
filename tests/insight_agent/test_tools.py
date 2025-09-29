import json
import os
import csv
import pytest

import litellm
from insight_agent.tools import intent_recognition_tool, metric_selection_tool
from insight_agent.contracts import IntentSchema


def test_intent_recognition_tool(monkeypatch):
    # For each schema intent, mock the LLM to return that intent when given an example question
    examples = {
        'sales_performance': "What are my sales?",
        'yoy_performance': "How did we perform vs last year?",
        'distribution_summary': "What is my distribution?",
        'pricing_summary': "How is my pricing?",
        'velocity_summary': "How fast are products selling?",
        'promotion_summary': "What was the impact of promotions?",
    }

    for intent_name, question in examples.items():
        def make_fake(intent_name):
            def fake_completion(*args, **kwargs):
                return json.dumps({"intent": intent_name, "entities": {"brand": "Jimmy Dean"}, "dimensions": ["category"]})
            return fake_completion

        monkeypatch.setattr(litellm, 'completion', make_fake(intent_name))
        out = intent_recognition_tool.func(question)
        parsed = json.loads(out)
        assert parsed["intent"] == intent_name
        assert parsed["entities"]["brand"] == "Jimmy Dean"
        assert parsed.get('dimensions') == ["category"]


def test_metric_selection_tool_reads_mapping(tmp_path, monkeypatch):
    # The metric_selection_tool should follow the IntentSchema mapping; assert all intents map to expected metrics
    expected = {
        'sales_performance': ["dollar_sales", "unit_sales", "volume_sales"],
        'yoy_performance': ["dollar_sales", "dollar_sales_ya", "unit_sales", "unit_sales_ya", "volume_sales", "volume_sales_ya"],
        'distribution_summary': ["tdp_ty", "tdp_ya"],
        'pricing_summary': ["avg_volume_price", "avg_volume_price_ya"],
        'velocity_summary': ["velocity", "velocity_ya"],
        'promotion_summary': ["promo_dollar_sales", "promo_dollar_sales_ya"],
    }

    for intent, metrics_expected in expected.items():
        metrics = metric_selection_tool.func(intent)
        assert metrics == metrics_expected
