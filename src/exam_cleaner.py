from __future__ import annotations

import re

import pandas as pd


STANDARD_COLUMNS = ["学校名称", "年级", "班级", "学生姓名", "学号", "考试名称", "科目", "成绩", "满分", "考试时间"]
NAME_ALIASES = {"姓名": "学生姓名", "学生": "学生姓名", "学生姓名": "学生姓名"}
CLASS_ALIASES = {"班级": "班级", "班级名称": "班级", "行政班": "班级"}
ID_ALIASES = {"学号": "学号", "学生编号": "学号", "账号": "学号"}


def clean_exam_scores(
    raw: pd.DataFrame,
    school_name: str,
    grade: str,
    exam_name: str,
    exam_date: str,
    full_score: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mapped = raw.rename(columns=_column_mapping(raw.columns))
    required = ["学生姓名", "班级", "学号"]
    missing = [column for column in required if column not in mapped.columns]
    if missing:
        raise ValueError(f"缺少必要字段: {', '.join(missing)}")

    subject_columns = [column for column in mapped.columns if column not in {"学生姓名", "班级", "学号"}]
    long_df = mapped.melt(
        id_vars=["学生姓名", "班级", "学号"],
        value_vars=subject_columns,
        var_name="科目",
        value_name="成绩",
    )
    long_df["学校名称"] = school_name
    long_df["年级"] = grade
    long_df["考试名称"] = exam_name
    long_df["满分"] = full_score
    long_df["考试时间"] = exam_date
    long_df["班级"] = long_df["班级"].map(normalize_class_name)
    long_df["成绩"] = long_df["成绩"].map(normalize_score)

    duplicate_mask = long_df.duplicated(subset=["考试名称", "科目", "学号", "班级"], keep=False)
    invalid_score_mask = long_df["成绩"].notna() & ((long_df["成绩"] < 0) | (long_df["成绩"] > full_score))
    missing_score_mask = long_df["成绩"].isna()

    issues = []
    for idx, row in long_df[duplicate_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "duplicate_student_subject", "message": f"{row['学生姓名']} {row['科目']} 重复"})
    for idx, row in long_df[invalid_score_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "invalid_score", "message": f"{row['学生姓名']} {row['科目']} 成绩超出范围"})
    for idx, row in long_df[missing_score_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "missing_or_absent_score", "message": f"{row['学生姓名']} {row['科目']} 缺考或成绩为空"})

    return long_df[STANDARD_COLUMNS], pd.DataFrame(issues)


def _column_mapping(columns: pd.Index) -> dict[str, str]:
    mapping = {}
    aliases = {**NAME_ALIASES, **CLASS_ALIASES, **ID_ALIASES}
    for column in columns:
        mapping[column] = aliases.get(str(column).strip(), str(column).strip())
    return mapping


def normalize_class_name(value: object) -> str:
    text = str(value).strip()
    match = re.match(r"(\d)0(\d)", text)
    if match:
        return f"{_cn_grade(match.group(1))}年级{match.group(2)}班"
    match = re.match(r"([一二三四五六七八九]|\d)年级?[\(（]?(\d)[\)）]?班?", text)
    if match:
        grade = _cn_grade(match.group(1))
        return f"{grade}年级{match.group(2)}班"
    match = re.match(r"([一二三四五六七八九])[\(（](\d)[\)）]班?", text)
    if match:
        return f"{match.group(1)}年级{match.group(2)}班"
    return text


def normalize_score(value: object) -> float | None:
    text = str(value).strip()
    if text in {"", "-", "缺考", "nan", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _cn_grade(value: str) -> str:
    mapping = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
    return mapping.get(value, value)
