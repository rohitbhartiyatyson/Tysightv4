import re
import os
import json


def _load_mapping_for_kind(kind: str):
    kinds_base = os.path.join('domain', 'catalog', 'kinds')
    kind_dir = os.path.join(kinds_base, kind)
    mapping = []
    if os.path.exists(kind_dir):
        versions = [d for d in os.listdir(kind_dir) if os.path.isdir(os.path.join(kind_dir, d))]
        versions = sorted(versions)
        for v in reversed(versions):
            eff = os.path.join(kind_dir, v, 'mapping_effective.json')
            if os.path.exists(eff):
                try:
                    with open(eff, 'r') as fh:
                        mapping = json.load(fh)
                        break
                except Exception:
                    pass
    return mapping


def _canonical_style(name: str) -> str:
    # chosen convention: snake_case, lowercase (e.g., num_col)
    # replace non-alnum with underscore, convert Camel/SHOUT to snake
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    # split camelcase
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    s = s.replace('__', '_')
    s = s.strip('_').lower()
    return s


def normalize_sql(sql: str, kind: str) -> str:
    # Harden: reject CTEs and subqueries to avoid unsafe SQL patterns
    # Reject common CTE usage (WITH ...) at the start of the query
    stripped = sql.lstrip()
    if re.match(r'(?i)^\s*WITH\b', stripped):
        # include machine-readable token for tests
        raise ValueError('DISALLOWED_CTE: CTE usage is disallowed in user SQL')

    # Detect explicit subquery patterns like FROM (SELECT ...) or EXISTS (SELECT ...)
    if re.search(r"(?i)FROM\s*\(\s*SELECT\b", sql) or re.search(r"(?i)EXISTS\s*\(\s*SELECT\b", sql):
        # include machine-readable token for tests
        raise ValueError('DISALLOWED_SUBQUERY: Subqueries are disallowed in user SQL')
    """Normalize SQL to enforce canonical naming style and symmetric LOWER() on string comparisons.

    - canonicalizes known column names to snake_case lowercase
    - rewrites comparisons like col = LOWER('v') to LOWER(col) = LOWER('v')
    - ensures LIMIT clause exists (no change here)
    """
    orig_sql = sql
    mapping = _load_mapping_for_kind(kind)
    # build map from original/canonical variants to desired form
    repl_map = {}
    if isinstance(mapping, list):
        for entry in mapping:
            oname = entry.get('original_name') or ''
            cname = entry.get('canonical_name') or ''
            target = cname or oname
            if target:
                target_style = _canonical_style(target)
                if oname:
                    repl_map[oname] = target_style
                if cname:
                    repl_map[cname] = target_style
    elif isinstance(mapping, dict):
        for k, v in mapping.items():
            target = v.get('canonical_name') or k
            repl_map[k] = _canonical_style(target)
            if v.get('original_name'):
                repl_map[v.get('original_name')] = _canonical_style(target)

    # Replace known identifiers (word boundaries)
    for k, v in sorted(repl_map.items(), key=lambda x: -len(x[0])):
        if not k:
            continue
        # replace in SQL regardless of case
        sql = re.sub(rf"\b{re.escape(k)}\b", v, sql, flags=re.IGNORECASE)

    # Ensure symmetric LOWER for comparisons against string literals
    # Pattern: <identifier> = LOWER('value')  -> LOWER(<identifier>) = LOWER('value')
    # use capture-based replacement below to safely handle quoting and content

    # Better approach: handle various quoting of literal, but do a simpler transform:
    def _sym_lower(match):
        left = match.group(1)
        quote = match.group(2)
        val = match.group(3)
        return f"LOWER({left}) = LOWER({quote}{val}{quote})"

    sql = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*)\b\s*=\s*LOWER\((['\"])(.*?)\2\)", _sym_lower, sql)

    return sql


def _escape_literal(val: str) -> str:
    return str(val).replace("'", "''")


def enforce_filters(sql: str, filters: dict) -> str:
    """Ensure provided filters appear in the SQL as case-insensitive predicates.

    - If filters is empty, return the original SQL
    - If filters non-empty and SQL lacks WHERE, insert one before GROUP BY/ORDER BY/HAVING
    - If SQL has WHERE, append AND (...)
    - Builds case-insensitive predicates using LOWER(col) = LOWER('val') or LOWER(col) IN (...)
    - Escapes single quotes in values
    - Preserves existing LIMIT clause (re-appends if necessary)
    """
    if not filters:
        return sql

    orig = sql or ''
    s = orig.strip()
    trailing_semicolon = s.endswith(';')
    if trailing_semicolon:
        s = s[:-1].rstrip()

    # Extract LIMIT clause if present
    limit_match = re.search(r"(?i)\blimit\s+\d+\b", s)
    limit_clause = ''
    if limit_match:
        limit_start = limit_match.start()
        limit_clause = s[limit_start:]
        s = s[:limit_start].rstrip()

    # Insert position before GROUP BY / ORDER BY / HAVING
    m = re.search(r"(?i)\b(group\s+by|order\s+by|having)\b", s)
    insert_pos = m.start() if m else len(s)

    preds = []
    for col, val in filters.items():
        if val in (None, ''):
            continue
        canon_col = _canonical_style(col)
        if isinstance(val, (list, tuple)):
            items = [f"LOWER('{_escape_literal(v)}')" for v in val if v not in (None, '')]
            if not items:
                continue
            preds.append(f"LOWER({canon_col}) IN ({', '.join(items)})")
        else:
            preds.append(f"LOWER({canon_col}) = LOWER('{_escape_literal(val)}')")

    if not preds:
        return orig

    predicates_str = ' AND '.join([f"({p})" for p in preds])

    head = s[:insert_pos]
    tail = s[insert_pos:]

    if re.search(r"(?i)\bwhere\b", head):
        new_head = head + ' AND ' + '(' + predicates_str + ')'
    else:
        new_head = head + ' WHERE ' + '(' + predicates_str + ')'

    final = new_head + tail
    if limit_clause:
        final = final.rstrip() + ' ' + limit_clause
    else:
        final = final.rstrip() + ' LIMIT 1000'

    if trailing_semicolon:
        final = final + ';'

    return final




class ValidationError(Exception):
    pass


def validate_sql(sql: str, kind: str):
    """Validate SQL against rails: canonical names, symmetric LOWER, LIMIT, whitelist FROM."""
    errors = []

    # LIMIT
    if not re.search(r"\blimit\s+\d+\b", sql, flags=re.IGNORECASE):
        errors.append('MISSING_LIMIT')

    # symmetric LOWER checks: find comparisons with string literal and ensure both sides use LOWER(
    comps = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*LOWER\((['\"])(.*?)\2\)", sql, flags=re.IGNORECASE)
    for left, q, val in comps:
        # if left is not wrapped with LOWER, it's a problem
        # but our normalize_sql should have fixed it; detect any remaining patterns of 'identifier = LOWER'
        if not re.search(rf"LOWER\(\s*{re.escape(left)}\s*\)", sql, flags=re.IGNORECASE):
            errors.append('ASYMMETRIC_LOWER')

    # whitelist FROM table names
    # find all FROM identifiers
    froms = re.findall(r"FROM\s+([`\"\[]?)([A-Za-z0-9_\.]+)\1", sql, flags=re.IGNORECASE)
    allowed = set()
    # allowed physical names: kind and 'data'
    allowed.add(kind)
    allowed.add('data')
    for _, tbl in froms:
        # strip schema if present
        tbl_simple = tbl.split('.')[-1]
        if tbl_simple.lower() not in {a.lower() for a in allowed}:
            errors.append(f'UNKNOWN_TABLE:{tbl}')

    # canonical name style: ensure identifiers are snake_case lowercase for known mapping
    mapping = _load_mapping_for_kind(kind)
    known = set()
    if isinstance(mapping, list):
        for e in mapping:
            oname = e.get('original_name')
            cname = e.get('canonical_name') or oname
            if cname:
                known.add(_canonical_style(cname))
            if oname:
                known.add(_canonical_style(oname))
    elif isinstance(mapping, dict):
        for k, v in mapping.items():
            known.add(_canonical_style(k))
            if v.get('canonical_name'):
                known.add(_canonical_style(v.get('canonical_name')))

    # check that identifiers used in SQL that match known names are in canonical style
    for ident in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", sql):
        low = ident.lower()
        if low in known and ident != low:
            errors.append(f'BAD_CANONICAL_STYLE:{ident}')

    if errors:
        raise ValidationError(','.join(errors))

    return True
