from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_loader import load_dataset
from src.exam_cleaner import clean_exam_scores, clean_grade_report
from src.metrics import build_analysis_tables, diagnose_rate_drop
from src.privacy import mask_dataframe
from src.query_agent import classify_intent, run_query_agent
from src.rag import embed_text, load_knowledge_documents, retrieve_knowledge, split_documents
from src.workflow import run_langgraph_query


DATA_DIR = ROOT / "data"


def test_metrics_tables_are_generated():
    data = load_dataset(DATA_DIR)
    tables = build_analysis_tables(data, "2026-06")

    assert not tables["product_usage"].empty
    assert not tables["group_training"].empty
    assert "qualification_rate" in tables["group_training"].columns


def test_rate_drop_diagnosis_has_required_fields():
    data = load_dataset(DATA_DIR)
    staff_name = data["staff"]["staff_name"].iloc[0]
    result = diagnose_rate_drop(data, staff_name, "2026-06", "2026-05")

    assert "current_rate" in result
    assert "previous_rate" in result
    assert "diagnosis" in result


def test_query_intent_classification():
    assert classify_intent("生成2026-06客户成功月报") == "monthly_report"
    assert classify_intent("为什么交付二组达标率下降") == "rate_drop_diagnosis"
    assert classify_intent("星学伴在不同学校的使用排名") == "product_school_ranking"
    assert classify_intent("培训达标率口径是什么") == "knowledge_rag"


def test_query_agent_sql_tool(tmp_path: Path):
    data = load_dataset(DATA_DIR)
    result = run_query_agent(
        "2026-06星学伴在不同学校的使用排名",
        data,
        "2026-06",
        "2026-05",
        tmp_path / "agent.db",
    )

    assert result.intent == "product_school_ranking"
    assert "ranking" in result.tables
    assert not result.tables["ranking"].empty


def test_rag_retrieves_training_policy():
    docs = retrieve_knowledge("培训达标率口径和40%阈值是什么", DATA_DIR / "knowledge")
    assert docs
    assert docs[0]["source"] == "training_policy.md"


def test_rag_chunking_and_embedding():
    documents = load_knowledge_documents(DATA_DIR / "knowledge")
    chunks = split_documents(documents)
    vector = embed_text(chunks[0].page_content)

    assert chunks
    assert len(vector) == 384
    assert chunks[0].metadata["source"]


def test_exam_cleaner_outputs_standard_template():
    raw = pd.read_csv(DATA_DIR / "exam_raw_sample.csv")
    cleaned, issues = clean_exam_scores(raw, "示例学校", "三年级", "六月阶段测试", "2026-06-20")

    assert list(cleaned.columns) == ["学校名称", "年级", "班级", "学生姓名", "学号", "考试名称", "科目", "成绩", "满分", "考试时间"]
    assert not issues.empty


def test_exam_cleaner_outputs_grade_report():
    raw = pd.DataFrame(
        {
            "学生": ["张三", "李四", "王五"],
            "班级": ["三年级1班", "301", "三年级2班"],
            "学生编号": ["2026001", "2026002", "2026003"],
            "语文成绩": [90, 80, 85],
            "数学": [95, 88, 92],
            "英语成绩": [91, 84, 93],
            "备注": ["", "", ""],
        }
    )
    report, issues = clean_grade_report(raw)

    assert list(report.columns) == ["姓名", "学号", "总分", "联排", "校排", "班排", "语文", "数学", "英语", "班级"]
    assert report["总分"].max() == 276
    assert set(report["班级"]) == {"三年级1班", "三年级2班"}
    assert issues.empty


def test_privacy_masking_changes_sensitive_values():
    data = load_dataset(DATA_DIR)
    masked = mask_dataframe(data["schools"].head(1))

    assert masked["school_name"].iloc[0] != data["schools"]["school_name"].iloc[0]
    assert masked["school_name"].iloc[0].startswith("学校_")


def test_langgraph_workflow_runs(tmp_path: Path):
    data = load_dataset(DATA_DIR)
    state = run_langgraph_query(
        "培训达标率口径和40%阈值是什么",
        data,
        "2026-06",
        "2026-05",
        tmp_path / "workflow.db",
    )

    assert state["answer"]
    assert state["llm_context"]
    assert any("LangGraph node" in step for step in state["trace"])
