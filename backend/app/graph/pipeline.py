"""Build, compile, and expose the ATS Optimization LangGraph pipeline.

Topology:
  START ─┬─→ cv_structurer ──┐
         └─→ job_analyzer  ──┴─→ matcher ──→ strengths_gaps ──→ planner ──→ optimizer ──→ validator
                                                                               ▲             │
                                                                               └─ (reoptimize)
                                                                                             ▼ (pass or max_iter)
                                                                                        generate_pdfs ──→ finalize ──→ END
"""

import asyncio
import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.graph.nodes.cv_structurer_node import cv_structurer_node
from app.graph.nodes.finalize_node import finalize_node
from app.graph.nodes.job_analyzer_node import job_analyzer_node
from app.graph.nodes.matcher_node import matcher_node
from app.graph.nodes.optimizer_node import optimizer_node
from app.graph.nodes.pdf_node import generate_pdfs_node
from app.graph.nodes.planner_node import planner_node
from app.graph.nodes.strengths_gaps_node import strengths_gaps_node
from app.graph.nodes.validator_node import validator_node
from app.graph.routing import should_generate, should_optimize, should_reoptimize
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

_DONE_SENTINEL = "__DONE__"


# ── Subgraphs ─────────────────────────────────────────────────────────────────

def build_resume_analysis_subgraph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("cv_structurer", cv_structurer_node)
    graph.add_edge(START, "cv_structurer")
    graph.add_edge("cv_structurer", END)
    return graph


def build_job_analysis_subgraph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("job_analyzer", job_analyzer_node)
    graph.add_edge(START, "job_analyzer")
    graph.add_edge("job_analyzer", END)
    return graph


def build_optimization_subgraph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("optimizer", optimizer_node)
    graph.add_node("generate_pdfs", generate_pdfs_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "optimizer")
    graph.add_conditional_edges(
        "optimizer",
        should_generate,
        {"generate_pdfs": "generate_pdfs", "end": END},
    )
    graph.add_edge("generate_pdfs", "finalize")
    graph.add_edge("finalize", END)
    return graph


resume_analysis_subgraph = build_resume_analysis_subgraph().compile()
job_analysis_subgraph = build_job_analysis_subgraph().compile()
optimization_subgraph = build_optimization_subgraph().compile()


# ── Main Full Graph ───────────────────────────────────────────────────────────

def build_optimization_graph() -> StateGraph:
    """Construct the full multi-agent ATS optimization state graph."""
    graph = StateGraph(GraphState)

    # ── Add Nodes ──
    graph.add_node("cv_structurer", cv_structurer_node)
    graph.add_node("job_analyzer", job_analyzer_node)
    graph.add_node("matcher", matcher_node)
    graph.add_node("strengths_gaps", strengths_gaps_node)
    graph.add_node("planner", planner_node)
    graph.add_node("optimizer", optimizer_node)
    graph.add_node("validator", validator_node)
    graph.add_node("generate_pdfs", generate_pdfs_node)
    graph.add_node("finalize", finalize_node)

    # ── Parallel Fan-out: START → cv_structurer & job_analyzer ──
    graph.add_edge(START, "cv_structurer")
    graph.add_edge(START, "job_analyzer")

    # ── Fan-in to Matcher ──
    graph.add_edge("cv_structurer", "matcher")
    graph.add_edge("job_analyzer", "matcher")

    # ── Linear flow: matcher → strengths_gaps → planner → optimizer → validator ──
    graph.add_edge("matcher", "strengths_gaps")
    graph.add_edge("strengths_gaps", "planner")
    graph.add_edge("planner", "optimizer")
    graph.add_edge("optimizer", "validator")

    # ── Conditional Loop: validator → should_reoptimize? ──
    graph.add_conditional_edges(
        "validator",
        should_reoptimize,
        {
            "optimize": "optimizer",
            "generate_pdfs": "generate_pdfs",
            "end": END,
        },
    )

    # ── Linear completion: generate_pdfs → finalize → END ──
    graph.add_edge("generate_pdfs", "finalize")
    graph.add_edge("finalize", END)

    return graph


# Single compiled graph singleton
optimization_graph = build_optimization_graph().compile()
logger.info("Multi-agent ATS optimization LangGraph compiled successfully.")


async def run_graph_pipeline(
    session_id: str,
    resume_text: str,
    jobs: list,
    output_mode: str,
    queue: asyncio.Queue,
) -> None:
    """Execute the optimization graph as a background task."""
    try:
        initial_state: Dict[str, Any] = {
            "session_id": session_id,
            "resume_text": resume_text,
            "jobs": jobs,
            "output_mode": output_mode,
            "queue": queue,
            "optimization_iteration": 0,
            "approved": False,
        }

        final_state = await optimization_graph.ainvoke(initial_state)

        if final_state.get("error"):
            await queue.put((
                "error",
                {"message": f"Falha no processamento: {final_state['error']}"},
            ))

    except Exception as exc:
        logger.exception("Graph pipeline failed for session %s", session_id)
        await queue.put((
            "error",
            {"message": f"Falha no processamento: {exc}"},
        ))

    finally:
        await queue.put(_DONE_SENTINEL)
