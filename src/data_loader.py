from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_FILES = {
    "schools": "schools.csv",
    "staff": "cs_staff.csv",
    "projects": "project_delivery.csv",
    "usage": "usage_records.csv",
    "training": "training_records.csv",
}


def load_dataset(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    root = Path(data_dir)
    return {name: pd.read_csv(root / filename) for name, filename in DATA_FILES.items()}


def validate_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [column for column in required if column not in df.columns]
