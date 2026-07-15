from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def build_sqlite_db(data: dict[str, pd.DataFrame], db_path: str | Path) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        for name, df in data.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
    return path


def run_sql(db_path: str | Path, query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def table_schema_summary(data: dict[str, pd.DataFrame]) -> list[dict]:
    return [
        {
            "table": name,
            "rows": int(len(df)),
            "columns": list(df.columns),
        }
        for name, df in data.items()
    ]
