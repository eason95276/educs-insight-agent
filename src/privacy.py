from __future__ import annotations

import hashlib

import pandas as pd


SENSITIVE_COLUMNS = {
    "school_name": "学校",
    "staff_name": "CS",
    "学生姓名": "学生",
    "学号": "ID",
}


def mask_value(value: object, prefix: str) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:6].upper()
    return f"{prefix}_{digest}"


def mask_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    masked = df.copy()
    for column, prefix in SENSITIVE_COLUMNS.items():
        if column in masked.columns:
            masked[column] = masked[column].map(lambda value: mask_value(value, prefix))
    return masked


def privacy_note() -> str:
    return (
        "隐私策略：学校、客户成功人员、学生和学号等敏感字段在进入大模型前进行哈希脱敏；"
        "结构化明细数据优先在本地用 Pandas 计算，仅将聚合摘要发送给 LLM。"
    )
