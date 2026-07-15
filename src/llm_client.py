from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
import requests

from src.cache import cache_key, read_cache, write_cache
from src.config import settings
from src.privacy import privacy_note
from src.token_budget import cost_note


MONTHLY_REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You generate verifiable, restrained, business-oriented customer success reports in Chinese.",
        ),
        (
            "user",
            """
You are an AI education customer success data analyst.

Generate a concise Chinese monthly report based only on the structured summary below.

Requirements:
1. Do not invent data outside the summary.
2. Include project overview, product usage, school performance, delivery group qualification rates, risks, and next-month suggestions.
3. The style should be suitable for a Feishu monthly report.
4. Mention that raw detailed data is processed locally and only aggregated summaries are sent to the LLM.

Privacy and cost constraints:
{privacy_note}
{cost_note}

Structured summary:
{summary_text}
""",
        ),
    ]
)


def generate_monthly_report(summary: dict) -> str:
    summary_text = json.dumps(summary, ensure_ascii=False, indent=2)
    key = cache_key({"type": "monthly_report", "summary": summary}, "llm")

    cached = read_cache(key)
    if cached:
        return cached + "\n\n> Cache hit: reused previous LLM report to save tokens."

    if not settings.deepseek_api_key:
        report = fallback_report(summary, summary_text)
        write_cache(key, report)
        return report

    messages = MONTHLY_REPORT_PROMPT.format_messages(
        privacy_note=privacy_note(),
        cost_note=cost_note(summary_text),
        summary_text=summary_text,
    )

    url = f"{settings.deepseek_base_url.rstrip('/')}/v1/chat/completions"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.deepseek_model,
            "messages": [_to_deepseek_message(message) for message in messages],
            "temperature": 0.3,
        },
        timeout=40,
    )
    response.raise_for_status()
    report = response.json()["choices"][0]["message"]["content"].strip()
    write_cache(key, report)
    return report


def _to_deepseek_message(message) -> dict:
    role = "user" if message.type == "human" else message.type
    return {"role": role, "content": message.content}


def fallback_report(summary: dict, summary_text: str) -> str:
    month = summary["month"]
    group_lines = []
    for row in summary.get("group_training", []):
        group_lines.append(
            f"- {row['group_name']}：达标率 {row['qualification_rate']:.1%}，"
            f"达标 {int(row['qualified_count'])}/{int(row['training_count'])}"
        )
    return "\n".join(
        [
            f"## {month} 客户成功业务月报",
            "",
            "### 交付组培训达标概览",
            *group_lines,
            "",
            "### 重点学校",
            "高使用学校和低使用学校已在看板中列出，建议优先关注低使用率学校的产品培训后数据沉淀情况。",
            "",
            "### 隐私与成本说明",
            privacy_note(),
            cost_note(summary_text),
            "",
            "> 当前未配置 DeepSeek API Key，因此使用本地模板生成报告。",
        ]
    )
