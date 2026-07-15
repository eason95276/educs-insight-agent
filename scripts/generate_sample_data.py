from __future__ import annotations

from pathlib import Path
import random

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


PRODUCTS = ["星学伴", "星乐读", "星未来", "鸿儒教研", "海班慧"]
SCHOOL_TYPES = ["自有校", "服务校", "市场校"]
GROUPS = ["交付一组", "交付二组", "交付三组"]
MONTHS = ["2026-04", "2026-05", "2026-06"]


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    schools = build_schools()
    staff = build_staff()
    projects = build_projects(schools, staff)
    usage = build_usage_records(schools, projects)
    training = build_training_records(projects, usage)
    raw_exam = build_raw_exam_scores()

    schools.to_csv(DATA_DIR / "schools.csv", index=False, encoding="utf-8-sig")
    staff.to_csv(DATA_DIR / "cs_staff.csv", index=False, encoding="utf-8-sig")
    projects.to_csv(DATA_DIR / "project_delivery.csv", index=False, encoding="utf-8-sig")
    usage.to_csv(DATA_DIR / "usage_records.csv", index=False, encoding="utf-8-sig")
    training.to_csv(DATA_DIR / "training_records.csv", index=False, encoding="utf-8-sig")
    raw_exam.to_csv(DATA_DIR / "exam_raw_sample.csv", index=False, encoding="utf-8-sig")

    print(f"Sample data generated in {DATA_DIR}")


def build_schools() -> pd.DataFrame:
    rows = []
    for idx in range(1, 25):
        rows.append(
            {
                "school_id": f"S{idx:03d}",
                "school_name": f"示例学校{idx}",
                "school_type": random.choice(SCHOOL_TYPES),
                "province": random.choice(["浙江", "江苏", "安徽", "上海"]),
                "city": random.choice(["杭州", "绍兴", "宁波", "南京", "合肥", "上海"]),
            }
        )
    return pd.DataFrame(rows)


def build_staff() -> pd.DataFrame:
    rows = []
    staff_aliases = [f"客户成功{chr(64 + idx)}" for idx in range(1, 10)]
    for idx, name in enumerate(staff_aliases, start=1):
        rows.append(
            {
                "staff_id": f"CS{idx:03d}",
                "staff_name": name,
                "group_name": GROUPS[(idx - 1) // 3],
            }
        )
    return pd.DataFrame(rows)


def build_projects(schools: pd.DataFrame, staff: pd.DataFrame) -> pd.DataFrame:
    rows = []
    project_id = 1
    for _, school in schools.iterrows():
        for product in random.sample(PRODUCTS, k=random.randint(2, 4)):
            owner = staff.sample(1, random_state=random.randint(1, 9999)).iloc[0]
            status = random.choices(
                ["未启动", "已启动", "已培训", "已验收"],
                weights=[0.08, 0.16, 0.28, 0.48],
                k=1,
            )[0]
            rows.append(
                {
                    "project_id": f"P{project_id:04d}",
                    "school_id": school["school_id"],
                    "product_name": product,
                    "staff_id": owner["staff_id"],
                    "status": status,
                    "planned_start_date": f"2026-0{random.randint(4, 6)}-{random.randint(1, 25):02d}",
                    "last_update_date": f"2026-06-{random.randint(8, 30):02d}",
                }
            )
            project_id += 1
    return pd.DataFrame(rows)


def build_usage_records(schools: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    school_type_bias = {"自有校": 0.18, "服务校": 0.08, "市场校": -0.08}
    for month in MONTHS:
        for _, project in projects.iterrows():
            school = schools.loc[schools["school_id"] == project["school_id"]].iloc[0]
            base = 0.46 + school_type_bias[school["school_type"]] + random.uniform(-0.18, 0.18)
            if project["status"] in {"未启动", "已启动"}:
                base -= 0.16
            teacher_total = random.randint(20, 80)
            student_total = random.randint(300, 1400)
            teacher_rate = clamp(base + random.uniform(-0.12, 0.12))
            student_rate = clamp(base + random.uniform(-0.14, 0.14))
            rows.append(
                {
                    "month": month,
                    "school_id": project["school_id"],
                    "project_id": project["project_id"],
                    "product_name": project["product_name"],
                    "teacher_total": teacher_total,
                    "teacher_active": int(teacher_total * teacher_rate),
                    "student_total": student_total,
                    "student_active": int(student_total * student_rate),
                    "data_update_date": f"2026-06-{random.randint(6, 30):02d}",
                }
            )
    return pd.DataFrame(rows)


def build_training_records(projects: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    product_weights = {
        "星未来": (0.7, 0.3),
        "星乐读": (0.3, 0.7),
        "星学伴": (0.5, 0.5),
        "鸿儒教研": (0.8, 0.2),
        "海班慧": (0.6, 0.4),
    }
    rows = []
    for _, usage_row in usage.iterrows():
        project = projects.loc[projects["project_id"] == usage_row["project_id"]].iloc[0]
        if project["status"] not in {"已培训", "已验收"}:
            continue
        teacher_rate = usage_row["teacher_active"] / max(usage_row["teacher_total"], 1)
        student_rate = usage_row["student_active"] / max(usage_row["student_total"], 1)
        tw, sw = product_weights[project["product_name"]]
        effect_score = teacher_rate * tw + student_rate * sw
        rows.append(
            {
                "month": usage_row["month"],
                "project_id": project["project_id"],
                "staff_id": project["staff_id"],
                "product_name": project["product_name"],
                "teacher_usage_rate": round(teacher_rate, 4),
                "student_usage_rate": round(student_rate, 4),
                "training_effect_score": round(effect_score, 4),
                "is_qualified": effect_score >= 0.4,
                "training_date": f"{usage_row['month']}-{random.randint(1, 25):02d}",
            }
        )
    return pd.DataFrame(rows)


def build_raw_exam_scores() -> pd.DataFrame:
    rows = []
    for idx in range(1, 13):
        rows.append(
            {
                "姓名": f"学生{idx}",
                "班级名称": random.choice(["三年级1班", "三(2)班", "301"]),
                "学号": f"2026{idx:04d}",
                "语文": random.choice([88, 92, "-", "缺考", 76]),
                "数学": random.choice([95, 84, 79, "-", "缺考"]),
                "英语": random.choice([90, 87, 83, "-", "缺考"]),
            }
        )
    rows.append(rows[0].copy())
    return pd.DataFrame(rows)


def clamp(value: float) -> float:
    return max(0.05, min(0.95, value))


if __name__ == "__main__":
    main()
