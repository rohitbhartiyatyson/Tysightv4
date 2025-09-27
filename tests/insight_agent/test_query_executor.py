import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from insight_agent.query_executor import execute_query


def test_execute_query(tmp_path):
    # Create a sample DataFrame and write to parquet
    df = pd.DataFrame({'a': [1,2,3], 'b':['x','y','z']})
    p = tmp_path / 'sample.parquet'
    df.to_parquet(p)

    # Create dataset directory and move parquet into expected path
    kind = 'test_kind'
    datasets_dir = os.path.join('domain','catalog','datasets')
    os.makedirs(os.path.join(datasets_dir, kind), exist_ok=True)
    dest = os.path.join(datasets_dir, kind, 'latest.parquet')
    # Use copy to avoid cross-device rename errors in CI/tmp dirs
    import shutil
    shutil.copy(p, dest)

    # Run execute_query
    res = execute_query(kind, 'SELECT * FROM dataset')
    assert isinstance(res, pd.DataFrame)
    assert list(res.columns) == ['a','b']
    assert res.shape[0] == 3

    # cleanup
    try:
        os.remove(dest)
        os.removedirs(os.path.join(datasets_dir, kind))
    except Exception:
        pass
