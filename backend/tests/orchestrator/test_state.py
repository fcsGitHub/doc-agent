"""Tests for DocumentState TypedDict shape and expected semantics."""

from orchestrator.state import DocumentState


def test_document_state_has_expected_fields() -> None:
    expected_keys = {
        "task_id",
        "current_phase",
        "section_ids",
        "current_section_index",
        "outline_approved",
        "review_round",
        "review_passed",
        "revision_needed_section_ids",
        "final_approved",
        "error",
        "progress_pct",
        "progress_message",
    }
    assert set(DocumentState.__annotations__.keys()) == expected_keys


def test_document_state_control_plane_only_usage() -> None:
    state: DocumentState = {
        "task_id": "task-1",
        "current_phase": "planning",
        "section_ids": ["sec-1", "sec-2"],
        "current_section_index": 0,
        "outline_approved": False,
        "review_round": 0,
        "review_passed": False,
        "revision_needed_section_ids": [],
        "final_approved": False,
        "error": None,
        "progress_pct": 0,
        "progress_message": "Initialized",
    }

    assert all(isinstance(section_id, str) for section_id in state["section_ids"])
    assert state["error"] is None
