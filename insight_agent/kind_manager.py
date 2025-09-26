def create_kind(uploaded_file, kind_name, sample_file=None):
    """Validate a mapping workbook uploaded via Streamlit and persist it.

    Args:
        uploaded_file: A file-like object as provided by st.file_uploader.
        kind_name (str): The name of the Kind to persist.
        sample_file: Optional file-like object for sample data.

    Returns:
        tuple: (success: bool, message: str)
    """
    import pandas as pd
    import os

    try:
        # Let pandas infer file type (Excel or CSV) based on the uploaded file
        # Streamlit's uploaded_file exposes a file-like object
        name = getattr(uploaded_file, 'name', '')
        if isinstance(name, str) and name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            # Reset stream pointer in case stream has been read
            try:
                uploaded_file.seek(0)
            except Exception:
                pass
            df = pd.read_csv(uploaded_file)
    except Exception as exc:
        return False, f"Error reading uploaded file: {exc}"

    required_cols = ["original_name", "canonical_name", "type", "description", "data_type"]
    if not all(col in df.columns for col in required_cols):
        missing = [c for c in required_cols if c not in df.columns]
        return False, f"Error: Missing required columns: {missing}. Please check the file."

    # Persist the validated DataFrame
    base_dir = os.path.join('domain', 'catalog', 'kinds', kind_name, 'v1')
    try:
        os.makedirs(base_dir, exist_ok=True)
        out_path = os.path.join(base_dir, 'required_mapping.csv')
        df.to_csv(out_path, index=False)
    except Exception as exc:
        return False, f"Error saving mapping file: {exc}"

    # Handle sample data and generate a simple autofill report
    if sample_file is not None:
        try:
            sname = getattr(sample_file, 'name', '')
            if isinstance(sname, str) and sname.lower().endswith(('.xls', '.xlsx')):
                sample_df = pd.read_excel(sample_file)
            else:
                try:
                    sample_file.seek(0)
                except Exception:
                    pass
                sample_df = pd.read_csv(sample_file)
        except Exception:
            # If sample file can't be read, continue but warn in message
            return False, "Error reading sample data file."

        # Infer format hints for each column in sample_df
        hints = []
        for col in sample_df.columns:
            series = sample_df[col]
            fmt = 'string'
            # try numeric
            try:
                _ = pd.to_numeric(series.dropna())
                fmt = 'numeric'
            except Exception:
                # try datetime
                try:
                    _ = pd.to_datetime(series.dropna())
                    fmt = 'datetime'
                except Exception:
                    fmt = 'string'
            hints.append((col, fmt))

        # Save nice_mapping.csv with original_name and format_hint
        try:
            nice_path = os.path.join(base_dir, 'nice_mapping.csv')
            with open(nice_path, 'w') as nf:
                nf.write('original_name,format_hint\n')
                for col, fmt in hints:
                    nf.write(f"{col},{fmt}\n")
        except Exception as exc:
            return False, f"Error saving nice mapping: {exc}"

        # Merge required_mapping.csv and nice_mapping.csv into mapping_effective.json
        try:
            req_df = pd.read_csv(out_path)
            nice_df = pd.read_csv(nice_path)
            # Merge required and nice mappings using an outer join to include sample-only columns
            merged = pd.merge(req_df, nice_df, on='original_name', how='outer')
            # Fill NA with empty strings for JSON-friendly output
            merged = merged.fillna('')
            # Convert to list of records
            records = merged.to_dict(orient='records')
            import json
            effective_path = os.path.join(base_dir, 'mapping_effective.json')
            with open(effective_path, 'w') as ef:
                json.dump(records, ef, indent=2)
        except Exception as exc:
            return False, f"Error generating effective mapping: {exc}"

        # Generate a markdown table for autofill_report.md summarizing the inferences
        try:
            report_lines = ['# Autofill Report', '', '| column | format_hint |', '|---|---|']
            for col, fmt in hints:
                report_lines.append(f'| {col} | {fmt} |')
            report = '\n'.join(report_lines)
            report_path = os.path.join(base_dir, 'autofill_report.md')
            with open(report_path, 'w') as fh:
                fh.write(report)
        except Exception as exc:
            return False, f"Error saving autofill report: {exc}"

        return True, f"Success! Kind '{kind_name}' created and autofill report generated."

    return True, f"Success! Kind '{kind_name}' created and mapping file saved."
