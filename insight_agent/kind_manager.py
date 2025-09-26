def create_kind(uploaded_file, kind_name):
    """Validate a mapping workbook uploaded via Streamlit and persist it.

    Args:
        uploaded_file: A file-like object as provided by st.file_uploader.
        kind_name (str): The name of the Kind to persist.

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

    return True, f"Success! Kind '{kind_name}' created and mapping file saved."
