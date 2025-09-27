import os
import csv
from insight_agent.instance_manager import onboard_instance


def test_onboard_instance_success(tmp_path):
    # Prepare a mock kind directory with mapping_effective.json
    kind_dir = os.path.join('domain', 'catalog', 'kinds', 'mock_kind', 'v1')
    os.makedirs(kind_dir, exist_ok=True)
    
    # Create a mapping with a filterable column and instance values
    mapping = [
        {"original_name": "a", "type": "market_or_store", "is_filterable": "yes", "filter_display_order": 1, "format_hint": "numeric"},
        {"original_name": "b", "type": "string", "is_filterable": "no", "format_hint": "string"},
    ]
    import json
    with open(os.path.join(kind_dir, 'mapping_effective.json'), 'w') as f:
        json.dump(mapping, f)

    # Create instance CSV matching columns a,b with some unique values
    inst_path = tmp_path / 'instance.csv'
    with open(inst_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['a', 'b'])
        writer.writerow(['store1', 'x'])
        writer.writerow(['store2', 'y'])
        writer.writerow(['store1', 'z'])

    with open(inst_path, 'rb') as inst_f:
        success, message = onboard_instance('mock_kind', inst_f)

    assert success is True
    # Check that latest.parquet was created
    latest_path = os.path.join('domain','catalog','datasets','mock_kind','latest.parquet')
    assert os.path.exists(latest_path)
    # Check profile.json exists and contains unique values for 'a'
    profile_path = os.path.join('domain','catalog','datasets','mock_kind','profile.json')
    assert os.path.exists(profile_path)
    with open(profile_path,'r') as pf:
        prof = json.load(pf)
    assert 'a' in prof
    # Verify profile now contains values and filter_display_order
    assert isinstance(prof['a'], dict)
    assert set(prof['a']['values']) == {'store1','store2'}
    assert prof['a']['filter_display_order'] == 1

    # cleanup dataset and profile
    try:
        os.remove(latest_path)
        os.remove(profile_path)
        os.removedirs(os.path.dirname(latest_path))
    except Exception:
        pass

    # cleanup mapping
    try:
        os.remove(os.path.join(kind_dir, 'mapping_effective.json'))
        os.removedirs(os.path.dirname(os.path.dirname(kind_dir)))
    except Exception:
        pass
