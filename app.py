from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.data_loader import load_dataset
from src.exam_cleaner import clean_exam_scores
from src.llm_client import generate_monthly_report
from src.metrics import build_analysis_tables, build_monthly_summary, diagnose_rate_drop
from src.privacy import mask_dataframe, privacy_note
from src.query_agent import run_query_agent
from src.token_budget import cost_note
from src.workflow import run_langgraph_query


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "educs_insight.db"

st.set_page_config(page_title="EduCS Insight Agent", layout="wide")


@st.cache_data
def cached_data() -> dict[str, pd.DataFrame]:
    return load_dataset(DATA_DIR)


def main() -> None:
    st.title("EduCS Insight Agent")
    st.caption("AI 教育产品客户成功分析与数据初始化智能体")

    data = cached_data()
    months = sorted(data["usage"]["month"].unique())

    tab_dashboard, tab_agent, tab_exam = st.tabs(
        ["客户成功看板", "Agent 问数与月报", "海班慧成绩清洗"]
    )

    with tab_dashboard:
        render_dashboard(data, months)

    with tab_agent:
        render_agent(data, months)

    with tab_exam:
        render_exam_cleaner()


def render_dashboard(data: dict[str, pd.DataFrame], months: list[str]) -> None:
    month = st.selectbox("选择月份", months, index=len(months) - 1, key="dashboard_month")
    tables = build_analysis_tables(data, month)

    st.subheader("项目交付总览")
    overview = tables["project_overview"]
    cols = st.columns(4)
    for idx, row in overview.head(4).iterrows():
        cols[idx % 4].metric(str(row["status"]), int(row["project_count"]))

    left, right = st.columns(2)
    with left:
        st.subheader("各产品使用率")
        st.dataframe(tables["product_usage"].round(4), use_container_width=True)
        st.subheader("学校使用排名")
        st.dataframe(tables["school_ranking"].head(10).round(4), use_container_width=True)
    with right:
        st.subheader("交付组培训达标率")
        st.dataframe(tables["group_training"].round(4), use_container_width=True)
        st.subheader("客户成功人员培训达标率")
        st.dataframe(tables["staff_training"].round(4), use_container_width=True)

    st.info(privacy_note())


def render_agent(data: dict[str, pd.DataFrame], months: list[str]) -> None:
    col_a, col_b, col_c = st.columns(3)
    current_month = col_a.selectbox("当前月份", months, index=len(months) - 1)
    previous_month = col_b.selectbox("对比月份", months, index=max(0, len(months) - 2))
    staff_name = col_c.selectbox("客户成功人员", sorted(data["staff"]["staff_name"].unique()))

    st.subheader("自然语言问数 Agent")
    examples = [
        f"为什么{staff_name}{current_month}达标率下降了？",
        f"{current_month}星学伴在不同学校的使用排名",
        f"{staff_name}负责的项目验收情况",
        "交付一组人员项目数",
        f"生成{current_month}客户成功月报",
        "培训达标率口径和40%阈值是什么",
        "这个系统如何节约token并保护隐私",
    ]
    question = st.text_input("输入业务问题", value=examples[0])
    st.caption("示例：" + " | ".join(examples[1:]))

    if st.button("运行 Agent", type="primary"):
        state = run_langgraph_query(
            question=question,
            data=data,
            current_month=current_month,
            previous_month=previous_month,
            db_path=DB_PATH,
        )
        result_tables = state.get("tables", {})
        llm_context = state.get("llm_context", {})
        st.markdown("### 回答")
        st.write(state.get("answer", "未生成回答"))

        st.markdown("### Agent 执行轨迹")
        for idx, step in enumerate(state.get("trace", []), start=1):
            st.write(f"{idx}. {step}")

        st.markdown("### 工具调用结果")
        if result_tables:
            for name, table in result_tables.items():
                st.write(f"**{name}**")
                st.dataframe(table, use_container_width=True)
        else:
            st.json(llm_context)

        st.markdown("### 发送给 LLM 前的上下文预览")
        st.json(llm_context)
        st.caption(cost_note(str(llm_context)))

    st.divider()
    st.subheader("结构化月报生成")
    tables = build_analysis_tables(data, current_month)
    summary = build_monthly_summary(tables, current_month)
    with st.expander("查看发送给 LLM 前的聚合摘要"):
        st.json(summary)
        st.caption(cost_note(str(summary)))

    if st.button("生成客户成功月报"):
        report = generate_monthly_report(summary)
        st.markdown(report)

    st.divider()
    st.subheader("达标率下降诊断快捷入口")
    if st.button("诊断当前人员"):
        result = diagnose_rate_drop(data, staff_name, current_month, previous_month)
        st.json(result)

    st.subheader("隐私脱敏示例")
    st.dataframe(mask_dataframe(data["schools"].head(5)), use_container_width=True)


def render_exam_cleaner() -> None:
    st.write("上传学校原始成绩单，清洗为海班慧标准导入模板。")
    uploaded = st.file_uploader("上传 CSV 成绩单", type=["csv"])
    raw = pd.read_csv(uploaded) if uploaded else pd.read_csv(DATA_DIR / "exam_raw_sample.csv")

    col1, col2, col3 = st.columns(3)
    school_name = col1.text_input("学校名称", "示例学校")
    grade = col2.text_input("年级", "三年级")
    exam_name = col3.text_input("考试名称", "六月阶段测试")
    exam_date = st.text_input("考试时间", "2026-06-20")

    st.subheader("原始成绩单")
    st.dataframe(raw, use_container_width=True)

    if st.button("清洗为标准模板"):
        cleaned, issues = clean_exam_scores(raw, school_name, grade, exam_name, exam_date)
        st.subheader("标准导入模板")
        st.dataframe(cleaned, use_container_width=True)
        st.download_button(
            "下载标准 CSV",
            cleaned.to_csv(index=False, encoding="utf-8-sig"),
            file_name="haibanhui_exam_template.csv",
            mime="text/csv",
        )
        st.subheader("异常报告")
        st.dataframe(issues, use_container_width=True)


if __name__ == "__main__":
    main()
