from __future__ import annotations

import pandas as pd


def add_rank(df: pd.DataFrame, sort_column: str) -> pd.DataFrame:
    ranked = df.sort_values(sort_column, ascending=False).reset_index(drop=True).copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked


def build_analysis_tables(data: dict[str, pd.DataFrame], month: str) -> dict[str, pd.DataFrame]:
    schools = data["schools"]
    staff = data["staff"]
    projects = data["projects"]
    usage = data["usage"]
    training = data["training"]

    usage_month = usage[usage["month"] == month].copy()
    training_month = training[training["month"] == month].copy()

    usage_enriched = (
        usage_month.merge(projects[["project_id", "staff_id", "status"]], on="project_id", how="left")
        .merge(schools[["school_id", "school_name", "school_type"]], on="school_id", how="left")
        .merge(staff, on="staff_id", how="left")
    )
    usage_enriched["teacher_usage_rate"] = usage_enriched["teacher_active"] / usage_enriched["teacher_total"].clip(lower=1)
    usage_enriched["student_usage_rate"] = usage_enriched["student_active"] / usage_enriched["student_total"].clip(lower=1)
    usage_enriched["combined_usage_rate"] = (
        usage_enriched["teacher_usage_rate"] * 0.5 + usage_enriched["student_usage_rate"] * 0.5
    )

    training_enriched = (
        training_month.merge(projects[["project_id", "school_id", "status"]], on="project_id", how="left")
        .merge(schools[["school_id", "school_name", "school_type"]], on="school_id", how="left")
        .merge(staff, on="staff_id", how="left")
    )

    project_overview = projects["status"].value_counts().rename_axis("status").reset_index(name="project_count")

    product_usage = add_rank(
        usage_enriched.groupby("product_name", as_index=False)
        .agg(
            teacher_usage_rate=("teacher_usage_rate", "mean"),
            student_usage_rate=("student_usage_rate", "mean"),
            combined_usage_rate=("combined_usage_rate", "mean"),
            project_count=("project_id", "nunique"),
        ),
        "combined_usage_rate",
    )

    school_ranking = add_rank(
        usage_enriched.groupby(["school_id", "school_name", "school_type"], as_index=False)
        .agg(
            combined_usage_rate=("combined_usage_rate", "mean"),
            teacher_usage_rate=("teacher_usage_rate", "mean"),
            student_usage_rate=("student_usage_rate", "mean"),
            product_count=("product_name", "nunique"),
        ),
        "combined_usage_rate",
    )

    staff_training = (
        training_enriched.groupby(["staff_id", "staff_name", "group_name"], as_index=False)
        .agg(
            training_count=("project_id", "count"),
            qualified_count=("is_qualified", "sum"),
            avg_effect_score=("training_effect_score", "mean"),
        )
    )
    staff_training["qualification_rate"] = staff_training["qualified_count"] / staff_training["training_count"].clip(lower=1)

    group_training = (
        staff_training.groupby("group_name", as_index=False)
        .agg(
            training_count=("training_count", "sum"),
            qualified_count=("qualified_count", "sum"),
            avg_effect_score=("avg_effect_score", "mean"),
        )
    )
    group_training["qualification_rate"] = group_training["qualified_count"] / group_training["training_count"].clip(lower=1)

    return {
        "usage_enriched": usage_enriched,
        "training_enriched": training_enriched,
        "project_overview": project_overview,
        "product_usage": product_usage,
        "school_ranking": school_ranking,
        "staff_training": add_rank(staff_training, "qualification_rate"),
        "group_training": add_rank(group_training, "qualification_rate"),
    }


def diagnose_rate_drop(data: dict[str, pd.DataFrame], staff_name: str, current_month: str, previous_month: str) -> dict:
    tables_current = build_analysis_tables(data, current_month)
    tables_previous = build_analysis_tables(data, previous_month)

    current = tables_current["staff_training"]
    previous = tables_previous["staff_training"]
    current_row = current[current["staff_name"] == staff_name]
    previous_row = previous[previous["staff_name"] == staff_name]

    if current_row.empty or previous_row.empty:
        return {"error": "没有找到该客户成功在两个对比月份的完整培训记录。"}

    c = current_row.iloc[0]
    p = previous_row.iloc[0]
    delta = float(c["qualification_rate"] - p["qualification_rate"])

    usage_current = tables_current["usage_enriched"]
    staff_usage = usage_current[usage_current["staff_name"] == staff_name]
    school_type_distribution = staff_usage["school_type"].value_counts(normalize=True).round(3).to_dict()
    stale_count = int((pd.to_datetime("2026-06-30") - pd.to_datetime(staff_usage["data_update_date"])).dt.days.gt(7).sum())

    reasons = []
    if c["training_count"] != p["training_count"]:
        reasons.append(f"培训项目数从 {int(p['training_count'])} 变为 {int(c['training_count'])}，样本量变化可能影响达标率。")
    if stale_count:
        reasons.append(f"存在 {stale_count} 条使用数据超过 7 天未更新，需先核查数据同步。")
    if school_type_distribution.get("市场校", 0) >= 0.35:
        reasons.append("当前负责项目中市场校占比较高，使用波动可能更明显。")
    if delta < -0.08:
        reasons.append("达标率下降超过 8 个百分点，建议优先检查低使用率学校和刚培训项目。")

    return {
        "staff_name": staff_name,
        "current_month": current_month,
        "previous_month": previous_month,
        "current_rate": round(float(c["qualification_rate"]), 4),
        "previous_rate": round(float(p["qualification_rate"]), 4),
        "delta": round(delta, 4),
        "current_training_count": int(c["training_count"]),
        "previous_training_count": int(p["training_count"]),
        "school_type_distribution": school_type_distribution,
        "stale_usage_rows": stale_count,
        "diagnosis": reasons or ["未发现明显数据质量或学校类型结构变化，建议进一步查看具体学校使用明细。"],
    }


def build_monthly_summary(tables: dict[str, pd.DataFrame], month: str) -> dict:
    group_training = tables["group_training"]
    product_usage = tables["product_usage"]
    school_ranking = tables["school_ranking"]
    project_overview = tables["project_overview"]
    staff_training = tables["staff_training"]

    return {
        "month": month,
        "project_overview": project_overview.to_dict(orient="records"),
        "top_products": product_usage.head(5).round(4).to_dict(orient="records"),
        "top_schools": school_ranking.head(5).round(4).to_dict(orient="records"),
        "bottom_schools": school_ranking.tail(5).round(4).to_dict(orient="records"),
        "group_training": group_training.round(4).to_dict(orient="records"),
        "low_training_staff": staff_training[staff_training["qualification_rate"] < 0.4].round(4).to_dict(orient="records"),
    }
