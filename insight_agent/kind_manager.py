def create_kind(uploaded_file):
    """Validate a mapping workbook uploaded via Streamlit.

    Args:
        uploaded_file: A file-like object as provided by st.file_uploader.

    Returns:
        tuple: (success: bool, message: str)
    """
    import pandas as pd

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
    if all(col in df.columns for col in required_cols):
        return True, "Validation successful!"
    else:
        missing = [c for c in required_cols if c not in df.columns]
        return False, f"Error: Missing required columns: {missing}. Please check the file."
