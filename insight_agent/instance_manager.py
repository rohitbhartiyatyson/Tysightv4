def onboard_instance(kind_name, instance_file):
    """Validate an instance file against the kind's effective mapping.

    Args:
        kind_name (str): The name of the kind to validate against.
        instance_file: file-like object for the instance data.

    Returns:
        tuple: (success: bool, message: str)
    """
    import os
    import pandas as pd
    import json

    base_dir = os.path.join('domain', 'catalog', 'kinds', kind_name, 'v1')
    effective_path = os.path.join(base_dir, 'mapping_effective.json')
    if not os.path.exists(effective_path):
        return False, f"Error: Effective mapping not found for kind '{kind_name}'."

    try:
        with open(effective_path, 'r') as ef:
            mapping = json.load(ef)
    except Exception as exc:
        return False, f"Error reading effective mapping: {exc}"

    try:
        name = getattr(instance_file, 'name', '')
        if isinstance(name, str) and name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(instance_file)
        else:
            try:
                instance_file.seek(0)
            except Exception:
                pass
            df = pd.read_csv(instance_file)
    except Exception as exc:
        return False, f"Error reading instance file: {exc}"

    # Extract expected columns from mapping
    expected = [rec.get('original_name') for rec in mapping if 'original_name' in rec]
    actual = list(df.columns)

    if set(expected) == set(actual):
        # Persist dataset to domain/catalog/datasets/<kind_name>/latest.parquet
        datasets_dir = os.path.join('domain', 'catalog', 'datasets', kind_name)
        os.makedirs(datasets_dir, exist_ok=True)
        out_path = os.path.join(datasets_dir, 'latest.parquet')
        try:
            # Rename columns from original_name -> canonical_name using mapping
            rename = {}
            for rec in mapping:
                orig = rec.get('original_name')
                canon = rec.get('canonical_name', orig)
                if orig and canon and orig != canon:
                    rename[orig] = canon
            if rename:
                df = df.rename(columns=rename)

            # Use parquet with zstd compression
            df.to_parquet(out_path, compression='zstd', index=False)
        except Exception as exc:
            return False, f"Error saving instance file: {exc}"

        # Read back the parquet and generate a profile for filterable columns
        try:
            df_saved = pd.read_parquet(out_path)
            # Identify filterable columns from mapping. A column is filterable if
            # filter_display_order contains a number. Ignore blanks.
            filterable_recs = []
            for rec in mapping:
                order_val = rec.get('filter_display_order')
                try:
                    if order_val is not None and str(order_val).strip() != '':
                        # attempt to parse integer; if it fails, skip
                        order_int = int(order_val)
                        filterable_recs.append((rec, order_int))
                except Exception:
                    continue

            profile = {}
            for rec, order_int in filterable_recs:
                col = rec.get('original_name')
                if col in df_saved.columns:
                    uniques = df_saved[col].dropna().unique().tolist()
                    # cap at 200
                    values = uniques[:200]
                    profile[col] = {
                        'values': values,
                        'filter_display_order': order_int
                    }

            profile_path = os.path.join(datasets_dir, 'profile.json')
            with open(profile_path, 'w') as pf:
                json.dump(profile, pf, indent=2)
        except Exception as exc:
            return False, f"Error profiling instance data: {exc}"

        return True, f"Success! Instance for '{kind_name}' has been saved and profiled."
    else:
        missing = [c for c in expected if c not in actual]
        extra = [c for c in actual if c not in expected]
        return False, f"Error: Instance columns do not match. Missing: {missing}. Extra: {extra}."
