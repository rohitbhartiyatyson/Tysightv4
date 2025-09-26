import os
import csv
from insight_agent.kind_manager import create_kind


def test_create_kind_success(tmp_path):
    # Create a temporary CSV file with required columns
    data = [
        ["original_name", "canonical_name", "type", "description", "data_type"],
        ["a", "A", "string", "desc", "text"],
    ]
    file_path = tmp_path / "mapping.csv"
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # Call create_kind with the temporary file and kind name
    # Provide a mock empty sample file as bytes
    with open(file_path, 'rb') as mapping_f:
        # create an empty sample file
        sample_path = tmp_path / "sample.csv"
        with open(sample_path, 'w', newline='') as sf:
            sf.write('num_col,str_col,date_col\n1,2,2020-01-01\n3,hello,2020-02-02')
        with open(sample_path, 'rb') as sample_f:
            success, message = create_kind(mapping_f, 'test_kind', sample_f)

    assert success is True

    out_path = os.path.join('domain', 'catalog', 'kinds', 'test_kind', 'v1', 'required_mapping.csv')
    report_path = os.path.join('domain', 'catalog', 'kinds', 'test_kind', 'v1', 'autofill_report.md')
    assert os.path.exists(out_path)
    assert os.path.exists(report_path)
    nice_path = os.path.join('domain','catalog','kinds','test_kind','v1','nice_mapping.csv')
    assert os.path.exists(nice_path)
    # Check nice_mapping contents
    with open(nice_path,'r') as nf:
        contents = nf.read()
    assert 'num_col' in contents and 'numeric' in contents
    assert 'str_col' in contents and 'string' in contents
    assert 'date_col' in contents and 'datetime' in contents
    # Check autofill report is not placeholder
    with open(report_path,'r') as rf:
        rpt = rf.read()
    assert 'Autofill Report' in rpt and 'num_col' in rpt

    # Check effective mapping JSON
    eff_path = os.path.join('domain','catalog','kinds','test_kind','v1','mapping_effective.json')
    assert os.path.exists(eff_path)
    import json
    with open(eff_path,'r') as ef:
        records = json.load(ef)
    # Ensure each record has original_name and format_hint
    assert any(r.get('original_name')=='num_col' and r.get('format_hint')=='numeric' for r in records)
    assert any(r.get('original_name')=='str_col' and r.get('format_hint')=='string' for r in records)
    assert any(r.get('original_name')=='date_col' and r.get('format_hint')=='datetime' for r in records)

    # Cleanup
    if os.path.exists(out_path):
        os.remove(out_path)
    if os.path.exists(report_path):
        os.remove(report_path)
    # Remove directories if empty
    try:
        os.removedirs(os.path.dirname(out_path))
    except Exception:
        pass


def test_create_kind_failure_missing_columns(tmp_path):
    # Create a temporary CSV file missing the 'data_type' column
    data = [
        ["original_name", "canonical_name", "type", "description"],
        ["a", "A", "string", "desc"],
    ]
    file_path = tmp_path / "mapping_invalid.csv"
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # Call create_kind with the invalid file and kind name
    with open(file_path, 'rb') as f:
        success, message = create_kind(f, 'test_kind_invalid')

    assert success is False
