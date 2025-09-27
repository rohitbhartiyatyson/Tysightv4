import os
import duckdb
import pandas as pd


def execute_query(kind_name: str, sql_query: str) -> pd.DataFrame:
    """Execute a SQL query against the latest Parquet file for a kind using duckdb.

    Args:
        kind_name: Name of the kind (dataset directory under domain/catalog/datasets).
        sql_query: SQL string that can reference the parquet file as a table using its path.

    Returns:
        pandas.DataFrame with query results.
    """
    datasets_dir = os.path.join('domain', 'catalog', 'datasets')
    parquet_path = os.path.join(datasets_dir, kind_name, 'latest.parquet')
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Parquet file not found for kind '{kind_name}': {parquet_path}")

    # Use duckdb to run SQL directly on the parquet file
    con = duckdb.connect(database=':memory:')
    try:
        # Create a view named 'dataset' that reads from the parquet file
        # using DuckDB's read_parquet function
        con.execute(f"CREATE VIEW dataset AS SELECT * FROM read_parquet('{parquet_path.replace('\\', '/') }')")
        df = con.execute(sql_query).df()
        return df
    finally:
        con.close()
