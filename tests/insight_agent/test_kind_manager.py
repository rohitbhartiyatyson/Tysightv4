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
    with open(file_path, 'rb') as f:
        success, message = create_kind(f, 'test_kind')

    assert success is True

    out_path = os.path.join('domain', 'catalog', 'kinds', 'test_kind', 'v1', 'required_mapping.csv')
    assert os.path.exists(out_path)

    # Cleanup
    if os.path.exists(out_path):
        os.remove(out_path)
        # Remove directories if empty
        try:
            os.removedirs(os.path.dirname(out_path))
        except Exception:
            pass
