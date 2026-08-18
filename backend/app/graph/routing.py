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


def should_reoptimize(state: GraphState) -> Literal["optimize", "finalize", "end"]:
    """Check validation status, iteration count, and ATS score progression to determine loop continuation.

    Guarantees termination:
    - If error -> end.
    - If score plateaued or decreased (latest score <= previous score) -> proceed to finalize.
    - If approved -> proceed to finalize.
    - If iteration count >= MAX_OPTIMIZATION_ITERATIONS (3) -> proceed to finalize.
    - Otherwise -> continue optimization loop.
    """
    if state.get("error"):
        return "end"

    iteration = state.get("optimization_iteration", 0)
    approved = state.get("approved", False)
    score_history = state.get("score_history", [])

    # 1. Check score progression
    if len(score_history) >= 2:
        prev_score = score_history[-2]
        latest_score = score_history[-1]
        if latest_score <= prev_score:
            logger.info(
                "Score ATS plateaued/did not improve (%d -> %d) at iteration %d — stopping optimization loop.",
                prev_score,
                latest_score,
                iteration,
            )
            return "finalize"

    # 2. Check full validation approval
    if approved:
        logger.info("Resume validation APPROVED after iteration %d — proceeding to finalize.", iteration)
        return "finalize"

    # 3. Check safety bound
    if iteration >= MAX_OPTIMIZATION_ITERATIONS:
        logger.warning(
            "Max optimization iterations (%d) reached without score improvement or approval. Proceeding to finalize.",
            MAX_OPTIMIZATION_ITERATIONS,
        )
        return "finalize"

    logger.info(
        "Optimization loop continuing (iteration %d/%d, score=%s) — running optimizer.",
        iteration,
        MAX_OPTIMIZATION_ITERATIONS,
        score_history[-1] if score_history else "N/A",
    )
    return "optimize"


def should_generate(state: GraphState) -> Literal["finalize", "end"]:
    """Check if optimization succeeded before finalizing."""
    if state.get("error"):
        return "end"

    if state.get("optimized_resumes"):
        return "finalize"

    return "end"
