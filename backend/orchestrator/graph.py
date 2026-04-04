"""LangGraph StateGraph skeleton for document generation workflow."""
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnusedCallResult=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator.nodes import (
    make_extract_node,
    make_generate_node,
    make_outline_node,
    make_parse_node,
    make_revise_node,
    make_reviews_node,
)
from orchestrator.state import DocumentState


def _advance(phase: str, progress_pct: int, progress_message: str) -> dict[str, object]:
    return {
        "current_phase": phase,
        "progress_pct": progress_pct,
        "progress_message": progress_message,
    }


def parse(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("parsing", 10, "Parsing source documents")


def extract_requirements(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("extracting", 20, "Extracting requirements")


def plan_outline(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("planning", 35, "Planning document outline")


def await_outline_approval(state: DocumentState) -> dict[str, object]:
    decision = interrupt(
        {
            "type": "outline_approval",
            "task_id": state["task_id"],
            "message": "Awaiting outline approval",
        }
    )
    approved = bool(decision) if decision is not None else state["outline_approved"]
    return {
        **_advance("planning", 40, "Outline approval received"),
        "outline_approved": approved,
    }


def generate_sections(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("generating", 60, "Generating document sections")


def run_reviews(state: DocumentState) -> dict[str, object]:
    return {
        **_advance("reviewing", 75, "Running automated reviews"),
        "review_round": state["review_round"] + 1,
    }


def check_review(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("reviewing", 80, "Evaluating review results")


def route_review(
    state: DocumentState,
) -> Literal["await_final_approval", "revise_sections"]:
    if state["review_passed"]:
        return "await_final_approval"
    if state["review_round"] < 3:
        return "revise_sections"
    return "await_final_approval"


def revise_sections(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("revising", 70, "Revising flagged sections")


def await_final_approval(state: DocumentState) -> dict[str, object]:
    decision = interrupt(
        {
            "type": "final_approval",
            "task_id": state["task_id"],
            "message": "Awaiting final approval",
        }
    )
    approved = bool(decision) if decision is not None else state["final_approved"]
    return {
        **_advance("reviewing", 90, "Final approval received"),
        "final_approved": approved,
    }


def export_document(state: DocumentState) -> dict[str, object]:
    _ = state
    return _advance("exporting", 100, "Exporting final document")


def build_document_graph(
    db: AsyncSession | None = None,
    llm_client: Any = None,
) -> StateGraph[DocumentState]:
    """Build the LangGraph workflow skeleton for document generation."""

    graph = StateGraph(DocumentState)

    if db is not None and llm_client is not None:
        graph.add_node("parse", make_parse_node(db, llm_client))
        graph.add_node("extract_requirements", make_extract_node(db, llm_client))
        graph.add_node("plan_outline", make_outline_node(db, llm_client))
        graph.add_node("generate_sections", make_generate_node(db, llm_client))
        graph.add_node("run_reviews", make_reviews_node(db, llm_client))
        graph.add_node("revise_sections", make_revise_node(db, llm_client))
    else:
        graph.add_node("parse", parse)
        graph.add_node("extract_requirements", extract_requirements)
        graph.add_node("plan_outline", plan_outline)
        graph.add_node("generate_sections", generate_sections)
        graph.add_node("run_reviews", run_reviews)
        graph.add_node("revise_sections", revise_sections)

    graph.add_node("await_outline_approval", await_outline_approval)
    graph.add_node("check_review", check_review)
    graph.add_node("await_final_approval", await_final_approval)
    graph.add_node("export_document", export_document)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "extract_requirements")
    graph.add_edge("extract_requirements", "plan_outline")
    graph.add_edge("plan_outline", "await_outline_approval")
    graph.add_edge("await_outline_approval", "generate_sections")
    graph.add_edge("generate_sections", "run_reviews")
    graph.add_edge("run_reviews", "check_review")
    graph.add_conditional_edges(
        "check_review",
        route_review,
        {
            "await_final_approval": "await_final_approval",
            "revise_sections": "revise_sections",
        },
    )
    graph.add_edge("revise_sections", "run_reviews")
    graph.add_edge("await_final_approval", "export_document")
    graph.add_edge("export_document", END)

    return graph
