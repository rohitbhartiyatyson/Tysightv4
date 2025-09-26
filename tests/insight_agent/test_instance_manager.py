import os
import csv
from insight_agent.instance_manager import onboard_instance


def test_onboard_instance_success(tmp_path):
    # Prepare a mock kind directory with mapping_effective.json
    kind_dir = os.path.join('domain', 'catalog', 'kinds', 'mock_kind', 'v1')
    os.makedirs(kind_dir, exist_ok=True)
    # Create a simple mapping_effective.json expecting columns a,b
    mapping = [
        {"original_name": "a", "format_hint": "numeric"},
        {"original_name": "b", "format_hint": "string"},
    ]
    import json
    with open(os.path.join(kind_dir, 'mapping_effective.json'), 'w') as f:
        json.dump(mapping, f)

    # Create instance CSV matching columns a,b
    inst_path = tmp_path / 'instance.csv'
    with open(inst_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['a', 'b'])
        writer.writerow(['1', 'x'])

    with open(inst_path, 'rb') as inst_f:
        success, message = onboard_instance('mock_kind', inst_f)

    assert success is True
    # cleanup
    try:
        os.remove(os.path.join(kind_dir, 'mapping_effective.json'))
        os.removedirs(os.path.dirname(os.path.dirname(kind_dir)))
    except Exception:
        pass
