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
                return json.dumps({"intent": intent_name, "entities": {"brand": "Jimmy Dean"}})
            return fake_completion

        monkeypatch.setattr(litellm, 'completion', make_fake(intent_name))
        out = intent_recognition_tool.func(question)
        parsed = json.loads(out)
        assert parsed["intent"] == intent_name
        assert parsed["entities"]["brand"] == "Jimmy Dean"


def test_metric_selection_tool_reads_mapping(tmp_path, monkeypatch):
    # Create a fake kind mapping file under domain/catalog/kinds/mykind/v1/required_mapping.csv
    base = tmp_path / "domain" / "catalog" / "kinds" / "mykind" / "v1"
    base.mkdir(parents=True)
    mapping_file = base / "required_mapping.csv"
    rows = [
        ["original_name","canonical_name","type","description","data_type","is_additive"],
        ["Brand","brand","Product attribution","Brand name","string",""],
        ["Dollar Sales","dollar_sales","POS measure","Dollar sales","decimal","yes"],
        ["Unit Sales","unit_sales","POS measure","Unit sales","decimal","yes"],
    ]
    with mapping_file.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)

    # Point tools to tmp domain
    monkeypatch.setenv('DOMAIN_CATALOG_ROOT', str(tmp_path / 'domain' / 'catalog'))
    # Also tell metric tool which kind to read
    monkeypatch.setenv('METRIC_KIND', 'mykind')

    metrics = metric_selection_tool.func('performance_summary')
    # Expect it to return the canonical names for POS measure columns
    assert 'dollar_sales' in metrics
    assert 'unit_sales' in metrics
