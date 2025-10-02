import pandas as pd
import math
from pathlib import Path

def read_excel(file_path, sheet_name=None):
    data = pd.read_excel(file_path, sheet_name=sheet_name)
    if isinstance(data, dict):  # если вернулся словарь, берём первый лист
        first_sheet = list(data.keys())[0]
        return data[first_sheet]
    return data

def read_input_excel(file_path, sheet_name=None):
    return read_excel(file_path, sheet_name)


def write_output_chunks(df, out_dir, base_name='output', chunk_size=5000):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(df)
    if total == 0:
        return []
    parts = math.ceil(total / chunk_size)
    paths = []
    for i in range(parts):
        start = i*chunk_size
        end = min(total, (i+1)*chunk_size)
        chunk = df.iloc[start:end].copy()
        path = out_dir / f"{base_name}_part{i+1}.xlsx"
        chunk.to_excel(path, index=False)
        paths.append(str(path))
    return paths