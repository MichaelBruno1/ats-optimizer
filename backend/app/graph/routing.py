"""Conditional routing functions for the ATS optimization LangGraph pipeline."""

import logging
from typing import Literal
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

MAX_OPTIMIZATION_ITERATIONS = 3


def should_optimize(state: GraphState) -> Literal["optimize", "end"]:
    """Check if analyses succeeded before proceeding to optimization."""
    if state.get("error"):
        logger.warning("Skipping optimization due to error: %s", state["error"])
        return "end"

    if state.get("structured_resume") and state.get("structured_jobs"):
        return "optimize"

    logger.warning("Missing structured analysis results — aborting graph.")
    return "end"


def should_reoptimize(state: GraphState) -> Literal["optimize", "generate_pdfs", "end"]:
    """Check validation status and iteration count to determine loop continuation.

    Guarantees loop termination:
    - If approved -> proceed to PDF generation.
    - If iteration count >= MAX_OPTIMIZATION_ITERATIONS (3) -> proceed to PDF generation.
    - If error -> end.
    - Otherwise -> re-optimize.
    """
    if state.get("error"):
        return "end"

    iteration = state.get("optimization_iteration", 0)
    approved = state.get("approved", False)

    if approved:
        logger.info("Resume validation APPROVED after iteration %d — proceeding to PDF generation.", iteration)
        return "generate_pdfs"

    if iteration >= MAX_OPTIMIZATION_ITERATIONS:
        logger.warning(
            "Max optimization iterations (%d) reached without full validation approval. Proceeding to PDF generation.",
            MAX_OPTIMIZATION_ITERATIONS,
        )
        return "generate_pdfs"

    logger.info("Validation pending approval (iteration %d/%d) — running optimizer loop.", iteration, MAX_OPTIMIZATION_ITERATIONS)
    return "optimize"


def should_generate(state: GraphState) -> Literal["generate_pdfs", "end"]:
    """Check if optimization succeeded before generating PDFs."""
    if state.get("error"):
        return "end"

    if state.get("optimized_resumes"):
        return "generate_pdfs"

    return "end"
