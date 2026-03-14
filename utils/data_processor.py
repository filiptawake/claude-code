import pandas as pd
import io


def process_uploaded_file(file_storage) -> str:
    """Read an uploaded CSV or Excel file and return a text summary."""
    filename = file_storage.filename.lower()
    content = file_storage.read()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError("Format nesuportat. Folosește CSV sau Excel (.xlsx/.xls).")

    summary_lines = [
        f"Fișier: {file_storage.filename}",
        f"Rânduri: {len(df)} | Coloane: {len(df.columns)}",
        f"Coloane: {', '.join(df.columns.tolist())}",
        "",
        "--- Primele 20 rânduri ---",
        df.head(20).to_string(index=False),
    ]

    # Append numeric stats if available
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        summary_lines += [
            "",
            "--- Statistici numerice ---",
            df[numeric_cols].describe().to_string(),
        ]

    return "\n".join(summary_lines)
