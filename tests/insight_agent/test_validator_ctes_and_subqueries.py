import pytest
from insight_agent.sql_validator import normalize_sql

# Positive (allowed): functions and parentheses but no FROM (should pass normalize)
def test_allowed_functions_and_parentheses():
    sqls = [
        "SELECT SUM(x) FROM data LIMIT 10",  # SUM with FROM data is allowed
        "SELECT myfunc(a, b) AS val LIMIT 100", # function call
        "SELECT col FROM data WHERE col LIKE 'A (test)' LIMIT 10",
        "SELECT * FROM data ORDER BY (col) LIMIT 5",
    ]
    for s in sqls:
        # should not raise DISALLOWED_CTE or DISALLOWED_SUBQUERY
        normalize_sql(s, 'data')

# Negative: CTE starting with WITH should be flagged
def test_disallow_cte():
    s = "WITH foo AS (SELECT 1) SELECT * FROM data"
    with pytest.raises(ValueError) as e:
        normalize_sql(s, 'data')
    assert 'DISALLOWED_CTE' in str(e.value)

# Negative: FROM (SELECT ...) should be flagged
def test_disallow_from_subquery():
    s = "SELECT * FROM (SELECT 1) t"
    with pytest.raises(ValueError) as e:
        normalize_sql(s, 'data')
    assert 'DISALLOWED_SUBQUERY' in str(e.value)

# Negative: WHERE EXISTS (SELECT ...) should be flagged
def test_disallow_exists_subquery():
    s = "SELECT * FROM data WHERE EXISTS (SELECT 1)"
    with pytest.raises(ValueError) as e:
        normalize_sql(s, 'data')
    assert 'DISALLOWED_SUBQUERY' in str(e.value)
