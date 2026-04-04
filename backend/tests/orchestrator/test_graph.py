"""Tests for LangGraph StateGraph skeleton and review routing behavior."""

from __future__ import annotations

from typing import cast

from orchestrator.graph import build_document_graph, route_review, run_reviews
from orchestrator.state import DocumentState


def _base_state(**overrides: object) -> DocumentState:
    state: DocumentState = {
        "task_id": "task-1",
        "current_phase": "parsing",
        "section_ids": ["sec-1", "sec-2"],
        "current_section_index": 0,
        "outline_approved": True,
        "review_round": 0,
        "review_passed": False,
        "revision_needed_section_ids": [],
        "final_approved": False,
        "error": None,
        "progress_pct": 0,
        "progress_message": "start",
    }
    for key, value in overrides.items():
        state[key] = value  # type: ignore[index]
    return state


def _apply_review_update(state: DocumentState) -> None:
    review_update = run_reviews(state)
    state["current_phase"] = cast(str, review_update["current_phase"])
    state["progress_pct"] = cast(int, review_update["progress_pct"])
    state["progress_message"] = cast(str, review_update["progress_message"])
    state["review_round"] = cast(int, review_update["review_round"])


def test_build_document_graph_has_expected_nodes_and_entry() -> None:
    graph = build_document_graph()

    expected_nodes = {
        "parse",
        "extract_requirements",
        "plan_outline",
        "await_outline_approval",
        "generate_sections",
        "run_reviews",
        "check_review",
        "revise_sections",
        "await_final_approval",
        "export_document",
    }

    assert set(graph.nodes.keys()) == expected_nodes
    assert ("__start__", "parse") in graph.edges


def test_build_document_graph_has_required_linear_edges() -> None:
    graph = build_document_graph()

    assert ("parse", "extract_requirements") in graph.edges
    assert ("extract_requirements", "plan_outline") in graph.edges
    assert ("plan_outline", "await_outline_approval") in graph.edges
    assert ("await_outline_approval", "generate_sections") in graph.edges
    assert ("generate_sections", "run_reviews") in graph.edges
    assert ("run_reviews", "check_review") in graph.edges
    assert ("revise_sections", "run_reviews") in graph.edges
    assert ("await_final_approval", "export_document") in graph.edges
    assert ("export_document", "__end__") in graph.edges


def test_check_review_conditional_edges_include_both_targets() -> None:
    graph = build_document_graph()
    branch_spec = next(iter(graph.branches["check_review"].values()))
    assert branch_spec.ends is not None

    assert branch_spec.ends["await_final_approval"] == "await_final_approval"
    assert branch_spec.ends["revise_sections"] == "revise_sections"


def test_route_review_goes_to_final_approval_when_passed() -> None:
    target = route_review(_base_state(review_passed=True, review_round=1))
    assert target == "await_final_approval"


def test_route_review_goes_to_revision_before_max_round() -> None:
    target = route_review(_base_state(review_passed=False, review_round=2))
    assert target == "revise_sections"


def test_route_review_forces_final_approval_after_max_round() -> None:
    target = route_review(_base_state(review_passed=False, review_round=3))
    assert target == "await_final_approval"


def test_graph_happy_path_progresses_until_final_approval_interrupt_point() -> None:
    graph = build_document_graph()
    app = graph.compile(
        interrupt_before=["await_outline_approval", "await_final_approval"],
    )

    result = app.invoke(_base_state(review_passed=True, review_round=0))

    assert result["current_phase"] == "planning"
    assert result["progress_pct"] == 35
    assert result["progress_message"] == "Planning document outline"


def test_graph_revision_loop_hits_final_approval_after_three_rounds() -> None:
    state = _base_state(review_passed=False, review_round=0)

    _apply_review_update(state)
    assert route_review(state) == "revise_sections"

    _apply_review_update(state)
    assert route_review(state) == "revise_sections"

    _apply_review_update(state)
    assert state["review_round"] == 3
    assert route_review(state) == "await_final_approval"
