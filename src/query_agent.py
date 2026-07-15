from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd

from src.metrics import build_analysis_tables, build_monthly_summary, diagnose_rate_drop
from src.rag import retrieve_knowledge
from src.sql_store import build_sqlite_db, run_sql
from src.token_budget import cost_note

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"


@dataclass
class AgentResult:
    intent: str
    answer: str
    trace: list[str]
    tables: dict[str, pd.DataFrame]
    llm_context: dict


def run_query_agent(
    question: str,
    data: dict[str, pd.DataFrame],
    current_month: str,
    previous_month: str,
    db_path: str | Path,
) -> AgentResult:
    trace = [
        "接收用户业务问题",
        "构建或刷新本地 SQLite 分析库",
    ]
    build_sqlite_db(data, db_path)

    intent = classify_intent(question)
    trace.append(f"识别任务意图：{intent}")

    if intent == "monthly_report":
        return _monthly_report(data, current_month, trace)
    if intent == "rate_drop_diagnosis":
        staff_name = _extract_staff_name(question, data["staff"]) or data["staff"]["staff_name"].iloc[0]
        return _rate_drop(data, staff_name, current_month, previous_month, trace)
    if intent == "product_school_ranking":
        product = _extract_product(question, data["usage"]) or data["usage"]["product_name"].iloc[0]
        return _product_school_ranking(product, current_month, db_path, trace)
    if intent == "acceptance_status":
        staff_name = _extract_staff_name(question, data["staff"]) or data["staff"]["staff_name"].iloc[0]
        return _acceptance_status(staff_name, db_path, trace)
    if intent == "group_workload":
        group_name = _extract_group(question, data["staff"]) or "交付一组"
        return _group_workload(group_name, db_path, trace)
    if intent == "knowledge_rag":
        return _knowledge_rag(question, Path(db_path).parent / "knowledge", trace)

    return _overview(data, current_month, trace)


def classify_intent(question: str) -> str:
    q = question.strip()
    if any(word in q for word in ["月报", "周报", "报告", "总结"]):
        return "monthly_report"
    if any(word in q for word in ["下降", "下滑", "同比", "环比", "原因"]):
        return "rate_drop_diagnosis"
    if "排名" in q or ("产品" in q and "学校" in q):
        return "product_school_ranking"
    if "验收" in q:
        return "acceptance_status"
    if "项目数" in q or "负载" in q or "负责" in q:
        return "group_workload"
    if any(word in q for word in ["口径", "规则", "隐私", "token", "成本", "上次", "历史", "SOP", "阈值", "40%"]):
        return "knowledge_rag"
    return "overview"


def _monthly_report(data: dict[str, pd.DataFrame], month: str, trace: list[str]) -> AgentResult:
    trace.extend(
        [
            "调用工具：build_analysis_tables",
            "调用工具：build_monthly_summary",
            "在调用 LLM 前压缩为聚合摘要",
        ]
    )
    tables = build_analysis_tables(data, month)
    summary = build_monthly_summary(tables, month)
    answer = (
        f"{month} 月报摘要已生成。系统只会把聚合指标发送给 LLM，不发送原始明细表。"
        f"{cost_note(str(summary))}"
    )
    return AgentResult("monthly_report", answer, trace, {"group_training": tables["group_training"]}, summary)


def _rate_drop(
    data: dict[str, pd.DataFrame],
    staff_name: str,
    current_month: str,
    previous_month: str,
    trace: list[str],
) -> AgentResult:
    trace.extend(
        [
            "调用工具：diagnose_rate_drop",
            "检查两个月达标率差异",
            "检查培训项目样本量变化",
            "检查使用数据是否长时间未更新",
            "分析学校类型结构变化",
        ]
    )
    result = diagnose_rate_drop(data, staff_name, current_month, previous_month)
    answer = _diagnosis_answer(result)
    return AgentResult("rate_drop_diagnosis", answer, trace, {}, result)


def _product_school_ranking(product: str, month: str, db_path: str | Path, trace: list[str]) -> AgentResult:
    trace.extend(
        [
            "调用 SQL 工具：按产品统计学校使用排名",
            "使用 SQL 聚合计算，避免把原始明细发送给 LLM",
        ]
    )
    query = _load_sql("product_school_ranking.sql")
    ranking = run_sql(db_path, query, (month, product))
    answer = f"已生成 {month} {product} 在不同学校的使用排名，共返回 {len(ranking)} 所学校。"
    return AgentResult("product_school_ranking", answer, trace, {"ranking": ranking}, {"month": month, "product": product})


def _acceptance_status(staff_name: str, db_path: str | Path, trace: list[str]) -> AgentResult:
    trace.extend(
        [
            "调用 SQL 工具：查询客户成功人员负责项目的验收状态",
            "按项目状态聚合统计",
        ]
    )
    query = _load_sql("acceptance_status_by_staff.sql")
    table = run_sql(db_path, query, (staff_name,))
    accepted = int(table.loc[table["status"] == "已验收", "project_count"].sum()) if not table.empty else 0
    total = int(table["project_count"].sum()) if not table.empty else 0
    answer = f"{staff_name} 当前负责项目中，已验收 {accepted}/{total} 个。"
    return AgentResult("acceptance_status", answer, trace, {"acceptance_status": table}, {"staff_name": staff_name})


def _group_workload(group_name: str, db_path: str | Path, trace: list[str]) -> AgentResult:
    trace.extend(
        [
            "调用 SQL 工具：查询交付组人员项目负载",
            "统计每位客户成功人员负责项目数、已验收数和未启动数",
        ]
    )
    query = _load_sql("group_workload.sql")
    table = run_sql(db_path, query, (group_name,))
    answer = f"已生成 {group_name} 的人员项目负载表，共 {len(table)} 位客户成功人员。"
    return AgentResult("group_workload", answer, trace, {"group_workload": table}, {"group_name": group_name})


def _knowledge_rag(question: str, knowledge_dir: str | Path, trace: list[str]) -> AgentResult:
    trace.extend(
        [
            "调用 RAG 工具：retrieve_knowledge",
            "检索业务口径、诊断手册和历史备注",
            "返回带来源依据的回答上下文",
        ]
    )
    docs = retrieve_knowledge(question, knowledge_dir)
    answer = "已检索到相关知识片段。请基于下方来源回答，不要凭空猜测。"
    context = {
        "question": question,
        "retrieved": docs,
    }
    return AgentResult("knowledge_rag", answer, trace, {}, context)


def _overview(data: dict[str, pd.DataFrame], month: str, trace: list[str]) -> AgentResult:
    trace.extend(["未命中特定工具，回退到月度概览", "构建月度核心分析表"])
    tables = build_analysis_tables(data, month)
    answer = "未匹配到更具体的分析工具，已返回月度概览。"
    return AgentResult(
        "overview",
        answer,
        trace,
        {"product_usage": tables["product_usage"], "group_training": tables["group_training"]},
        {"month": month},
    )


def _extract_staff_name(question: str, staff: pd.DataFrame) -> str | None:
    for name in staff["staff_name"].tolist():
        if name in question:
            return str(name)
    match = re.search(r"CS\d{3}", question)
    if match:
        row = staff[staff["staff_id"] == match.group(0)]
        if not row.empty:
            return str(row.iloc[0]["staff_name"])
    return None


def _extract_product(question: str, usage: pd.DataFrame) -> str | None:
    for product in sorted(usage["product_name"].unique(), key=len, reverse=True):
        if product in question:
            return str(product)
    return None


def _extract_group(question: str, staff: pd.DataFrame) -> str | None:
    for group in sorted(staff["group_name"].unique(), key=len, reverse=True):
        if group in question:
            return str(group)
    return None


def _diagnosis_answer(result: dict) -> str:
    if "error" in result:
        return result["error"]
    delta = result["delta"]
    direction = "下降" if delta < 0 else "上升"
    reasons = " ".join(result.get("diagnosis", []))
    return (
        f"{result['staff_name']} 在 {result['current_month']} 的培训达标率较 "
        f"{result['previous_month']} {direction}了 {abs(delta):.1%}。{reasons}"
    )


def _load_sql(filename: str) -> str:
    return (SQL_DIR / filename).read_text(encoding="utf-8")
