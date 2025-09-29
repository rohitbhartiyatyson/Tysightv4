import json
import os
import csv
import pytest

import litellm
from insight_agent.tools import intent_recognition_tool, metric_selection_tool


def test_intent_recognition_tool(monkeypatch):
    # Mock LLM to return a JSON intent
    def fake_completion(*args, **kwargs):
        return json.dumps({"intent": "performance_summary", "entities": {"brand": "Jimmy Dean"}})

    monkeypatch.setattr(litellm, 'completion', fake_completion)

    out = intent_recognition_tool.func("how did jimmy dean perform?")
    parsed = json.loads(out)

    assert parsed["intent"] == "performance_summary"
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
