"""Unit tests for LangGraph conditional routing."""

from app.graph.routing import should_reoptimize
from app.graph.state import GraphState


def test_should_reoptimize_approved() -> None:
    state: GraphState = {"approved": True, "optimization_iteration": 1}
    assert should_reoptimize(state) == "finalize"


def test_should_reoptimize_max_iterations() -> None:
    state: GraphState = {"approved": False, "optimization_iteration": 3}
    assert should_reoptimize(state) == "finalize"


def test_should_reoptimize_score_not_improving() -> None:
    state: GraphState = {
        "approved": False,
        "optimization_iteration": 2,
        "score_history": [85, 82],
    }
    assert should_reoptimize(state) == "finalize"


def test_should_reoptimize_continue_loop() -> None:
    state: GraphState = {
        "approved": False,
        "optimization_iteration": 1,
        "score_history": [75],
    }
    assert should_reoptimize(state) == "optimize"
