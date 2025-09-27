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
        # Normalize path for SQL
        parquet_sql_path = parquet_path.replace('\\','/')
        # Create a view named 'data' that reads from the parquet file
        con.execute(f"CREATE VIEW data AS SELECT * FROM read_parquet('{parquet_sql_path}')")

        # Replace table references in the incoming SQL to point to 'data'
        import re
        def replace_from(match):
            # match.group(1) is the FROM keyword + whitespace
            # match.group(2) is the table identifier (may be quoted/backticked)
            from_kw = match.group(1)
            # replace with FROM data
            return f"{from_kw}data"

        # Use a regex to find FROM <identifier> (handles backticks, quotes, brackets, schema.table).
        # Match patterns like: FROM `my table`, FROM "my table", FROM 'my table', FROM [my table], FROM schema.table, FROM table
        pattern = r"(FROM\s+)(`[^`]+`|\"[^\"]+\"|'[^']+'|\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)"
        sql_fixed = re.sub(pattern, replace_from, sql_query, flags=re.IGNORECASE)

        df = con.execute(sql_fixed).df()
        return df
    finally:
        con.close()
