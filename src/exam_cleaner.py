from __future__ import annotations

import re

import pandas as pd


STANDARD_COLUMNS = ["学校名称", "年级", "班级", "学生姓名", "学号", "考试名称", "科目", "成绩", "满分", "考试时间"]
GRADE_REPORT_BASE_COLUMNS = ["姓名", "总分", "联排", "校排", "班排"]
DEFAULT_SUBJECT_ORDER = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]
NAME_ALIASES = {"姓名": "学生姓名", "学生": "学生姓名", "学生姓名": "学生姓名"}
CLASS_ALIASES = {"班级": "班级", "班级名称": "班级", "行政班": "班级"}
ID_ALIASES = {"学号": "学号", "学生编号": "学号", "账号": "学号"}
FULL_SCORE_ALIASES = {"满分": "满分", "试卷满分": "满分"}
TOTAL_ALIASES = {"总分": "总分", "合计": "总分", "总成绩": "总分"}
RANK_ALIASES = {"联排": "联排", "联考排名": "联排", "校排": "校排", "学校排名": "校排", "班排": "班排", "班级排名": "班排"}
IGNORED_COLUMNS = {"考试时间", "考试日期", "日期", "任课老师", "老师", "备注"}


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

    subject_columns = _subject_columns(mapped.columns)
    if not subject_columns:
        raise ValueError("没有识别到成绩科目列，请确认表格中包含语文、数学、英语等成绩字段。")

    id_vars = ["学生姓名", "班级", "学号"]
    if "满分" in mapped.columns:
        id_vars.append("满分")

    long_df = mapped.melt(
        id_vars=id_vars,
        value_vars=subject_columns,
        var_name="科目",
        value_name="成绩",
    )
    long_df["学校名称"] = school_name
    long_df["年级"] = grade
    long_df["考试名称"] = exam_name
    if "满分" in mapped.columns:
        long_df["满分"] = long_df["满分"].map(normalize_score).fillna(full_score)
    else:
        long_df["满分"] = full_score
    long_df["考试时间"] = exam_date
    long_df["班级"] = long_df["班级"].map(normalize_class_name)
    long_df["学号"] = long_df["学号"].map(normalize_student_id)
    long_df["科目"] = long_df["科目"].map(normalize_subject_name)
    long_df["成绩"] = long_df["成绩"].map(normalize_score)

    duplicate_mask = long_df.duplicated(subset=["考试名称", "科目", "学号", "班级"], keep=False)
    invalid_score_mask = long_df["成绩"].notna() & ((long_df["成绩"] < 0) | (long_df["成绩"] > long_df["满分"]))
    missing_score_mask = long_df["成绩"].isna()
    missing_id_mask = long_df["学号"].isna() | long_df["学号"].astype(str).str.strip().eq("")

    issues = []
    for idx, row in long_df[missing_id_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "missing_student_id", "message": f"{row['学生姓名']} 缺少学号"})
    for idx, row in long_df[duplicate_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "duplicate_student_subject", "message": f"{row['学生姓名']} {row['科目']} 重复"})
    for idx, row in long_df[invalid_score_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "invalid_score", "message": f"{row['学生姓名']} {row['科目']} 成绩超出范围"})
    for idx, row in long_df[missing_score_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "missing_or_absent_score", "message": f"{row['学生姓名']} {row['科目']} 缺考或成绩为空"})

    return long_df[STANDARD_COLUMNS], pd.DataFrame(issues)


def clean_grade_report(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mapped = raw.rename(columns=_column_mapping(raw.columns))
    required = ["学生姓名", "班级"]
    missing = [column for column in required if column not in mapped.columns]
    if missing:
        raise ValueError(f"缺少必要字段: {', '.join(missing)}")

    mapped["学生姓名"] = mapped["学生姓名"].astype(str).str.strip()
    mapped["班级"] = mapped["班级"].map(normalize_class_name)
    if "学号" in mapped.columns:
        mapped["学号"] = mapped["学号"].map(normalize_student_id)

    subject_columns = _subject_columns(mapped.columns)
    if not subject_columns:
        raise ValueError("没有识别到成绩科目列，请确认表格中包含语文、数学、英语等成绩字段。")

    report = pd.DataFrame(
        {
            "姓名": mapped["学生姓名"],
            "班级": mapped["班级"],
        }
    )
    if "学号" in mapped.columns:
        report.insert(1, "学号", mapped["学号"])

    normalized_subjects = []
    for column in subject_columns:
        subject = normalize_subject_name(column)
        normalized_subjects.append(subject)
        report[subject] = mapped[column].map(normalize_score)

    subject_columns_normalized = _ordered_subjects(normalized_subjects)
    if "总分" in mapped.columns:
        report["总分"] = mapped["总分"].map(normalize_score)
    else:
        report["总分"] = report[subject_columns_normalized].sum(axis=1, min_count=1)

    if "联排" in mapped.columns:
        report["联排"] = mapped["联排"].map(normalize_rank)
    else:
        report["联排"] = report["总分"].rank(method="min", ascending=False).astype("Int64")
    if "校排" in mapped.columns:
        report["校排"] = mapped["校排"].map(normalize_rank)
    else:
        report["校排"] = report["总分"].rank(method="min", ascending=False).astype("Int64")
    if "班排" in mapped.columns:
        report["班排"] = mapped["班排"].map(normalize_rank)
    else:
        report["班排"] = report.groupby("班级")["总分"].rank(method="min", ascending=False).astype("Int64")

    ordered_columns = ["姓名", "总分", "联排", "校排", "班排", *subject_columns_normalized]
    if "学号" in report.columns:
        ordered_columns.insert(1, "学号")
    ordered_columns.append("班级")

    issues = _build_grade_report_issues(report, subject_columns_normalized)
    report = report.sort_values(["班级", "班排", "姓名"], kind="stable").reset_index(drop=True)
    return report[ordered_columns], pd.DataFrame(issues)


def _column_mapping(columns: pd.Index) -> dict[str, str]:
    mapping = {}
    aliases = {**NAME_ALIASES, **CLASS_ALIASES, **ID_ALIASES, **FULL_SCORE_ALIASES, **TOTAL_ALIASES, **RANK_ALIASES}
    for column in columns:
        mapping[column] = aliases.get(str(column).strip(), str(column).strip())
    return mapping


def _subject_columns(columns: pd.Index) -> list[str]:
    base_columns = {"学生姓名", "班级", "学号", "满分", "总分", "联排", "校排", "班排", *IGNORED_COLUMNS}
    return [column for column in columns if column not in base_columns]


def _ordered_subjects(subjects: list[str]) -> list[str]:
    seen = set()
    ordered = [subject for subject in DEFAULT_SUBJECT_ORDER if subject in subjects and not (subject in seen or seen.add(subject))]
    ordered.extend(subject for subject in subjects if subject not in seen and not seen.add(subject))
    return ordered


def _build_grade_report_issues(report: pd.DataFrame, subject_columns: list[str]) -> list[dict]:
    issues = []
    duplicate_mask = report.duplicated(subset=["姓名", "班级"], keep=False)
    for idx, row in report[duplicate_mask].iterrows():
        issues.append({"row": int(idx), "issue_type": "duplicate_student", "message": f"{row['姓名']} 在 {row['班级']} 重复"})

    if "学号" in report.columns:
        missing_id_mask = report["学号"].isna() | report["学号"].astype(str).str.strip().eq("")
        for idx, row in report[missing_id_mask].iterrows():
            issues.append({"row": int(idx), "issue_type": "missing_student_id", "message": f"{row['姓名']} 缺少学号"})

    for subject in subject_columns:
        missing_mask = report[subject].isna()
        for idx, row in report[missing_mask].iterrows():
            issues.append({"row": int(idx), "issue_type": "missing_or_absent_score", "message": f"{row['姓名']} {subject} 缺考或成绩为空"})

    return issues


def normalize_class_name(value: object) -> str:
    text = str(value).strip()
    text = text.replace("（", "(").replace("）", ")")
    match = re.match(r"(\d)0(\d)", text)
    if match:
        return f"{_cn_grade(match.group(1))}年级{match.group(2)}班"
    match = re.match(r"([一二三四五六七八九]|\d)年级?[\(]?([一二三四五六七八九]|\d)[\)]?班?", text)
    if match:
        grade = _cn_grade(match.group(1))
        class_no = _arabic_digit(match.group(2))
        return f"{grade}年级{class_no}班"
    match = re.match(r"([一二三四五六七八九])[\(]([一二三四五六七八九]|\d)[\)]班?", text)
    if match:
        class_no = _arabic_digit(match.group(2))
        return f"{match.group(1)}年级{class_no}班"
    return text


def normalize_subject_name(value: object) -> str:
    text = str(value).strip()
    return re.sub(r"(成绩|分数)$", "", text)


def normalize_student_id(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def normalize_score(value: object) -> float | None:
    text = str(value).strip()
    if text in {"", "-", "缺考", "nan", "None"}:
        return None
    text = text.removesuffix("分")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_rank(value: object) -> int | None:
    score = normalize_score(value)
    if score is None:
        return None
    return int(score)


def _cn_grade(value: str) -> str:
    mapping = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
    return mapping.get(value, value)


def _arabic_digit(value: str) -> str:
    mapping = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
    return mapping.get(value, value)
