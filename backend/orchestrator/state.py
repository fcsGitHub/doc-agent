"""LangGraph control-plane state for document orchestration."""

from typing import TypedDict


class DocumentState(TypedDict):
    """Workflow state passed between LangGraph nodes.

    State intentionally stores only identifiers and control flags.
    Document content remains persisted in the database.
    """

    task_id: str
    current_phase: str  # "parsing", "extracting", "planning", "generating", "reviewing", "revising", "exporting"
    section_ids: list[str]  # IDs only — content lives in DB
    current_section_index: int
    outline_approved: bool
    review_round: int  # tracks revision loop count (max 3 per G8)
    review_passed: bool
    revision_needed_section_ids: list[str]
    final_approved: bool
    error: str | None
    progress_pct: int  # 0-100 for SSE updates
    progress_message: str
