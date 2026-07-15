from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
from langgraph.graph import END, StateGraph

from src.query_agent import AgentResult, classify_intent, run_query_agent


class EduCSState(TypedDict, total=False):
    question: str
    data: dict[str, pd.DataFrame]
    current_month: str
    previous_month: str
    db_path: str
    intent: str
    trace: list[str]
    result: AgentResult
    answer: str
    tables: dict[str, pd.DataFrame]
    llm_context: dict[str, Any]


def build_query_workflow():
    graph = StateGraph(EduCSState)
    graph.add_node("route_intent", route_intent)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("prepare_response", prepare_response)

    graph.set_entry_point("route_intent")
    graph.add_edge("route_intent", "execute_tool")
    graph.add_edge("execute_tool", "prepare_response")
    graph.add_edge("prepare_response", END)
    return graph.compile()


def run_langgraph_query(
    question: str,
    data: dict[str, pd.DataFrame],
    current_month: str,
    previous_month: str,
    db_path: str | Path,
) -> EduCSState:
    workflow = build_query_workflow()
    return workflow.invoke(
        {
            "question": question,
            "data": data,
            "current_month": current_month,
            "previous_month": previous_month,
            "db_path": str(db_path),
            "trace": ["LangGraph workflow started"],
        }
    )


def route_intent(state: EduCSState) -> EduCSState:
    intent = classify_intent(state["question"])
    trace = state.get("trace", []) + [f"LangGraph node route_intent -> {intent}"]
    return {"intent": intent, "trace": trace}


def execute_tool(state: EduCSState) -> EduCSState:
    result = run_query_agent(
        question=state["question"],
        data=state["data"],
        current_month=state["current_month"],
        previous_month=state["previous_month"],
        db_path=state["db_path"],
    )
    trace = state.get("trace", []) + ["LangGraph node execute_tool -> run_query_agent"]
    return {"result": result, "trace": trace}


def prepare_response(state: EduCSState) -> EduCSState:
    result = state["result"]
    trace = state.get("trace", []) + ["LangGraph node prepare_response -> package answer/tables/context"]
    return {
        "answer": result.answer,
        "tables": result.tables,
        "llm_context": result.llm_context,
        "trace": trace + result.trace,
    }
