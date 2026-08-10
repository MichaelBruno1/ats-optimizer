"""Conditional edge functions for the ATS optimization graph.

These determine whether the pipeline should proceed to the next stage
or short-circuit to END based on error state.
"""

import logging
from typing import Literal

from .state import GraphState

logger = logging.getLogger(__name__)


def should_optimize(state: GraphState) -> Literal["optimize", "end"]:
    """Check if both analyses succeeded before proceeding to optimization."""
    if state.get("error"):
        logger.warning("Skipping optimization — prior error: %s", state["error"])
        return "end"

    has_resume = state.get("resume_analysis") is not None
    has_jobs = state.get("job_analyses") is not None

    if has_resume and has_jobs:
        logger.info("Both analyses complete — proceeding to optimization.")
        return "optimize"

    logger.warning("Missing analysis results — aborting pipeline.")
    return "end"


def should_generate(state: GraphState) -> Literal["generate_pdfs", "end"]:
    """Check if optimization succeeded before generating PDFs."""
    if state.get("error"):
        logger.warning("Skipping PDF generation — prior error: %s", state["error"])
        return "end"

    if state.get("optimized_resumes"):
        logger.info("Optimization complete — proceeding to PDF generation.")
        return "generate_pdfs"

    logger.warning("No optimized resumes available — aborting pipeline.")
    return "end"
