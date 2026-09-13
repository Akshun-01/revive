"""Graph construction + compile.

Slice edges are linear (see LLD section 11). Branch after resolve: a failed customer
resolution short-circuits to END. Actions / approval / verification are appended in step 5.

The compiled graph is a process-wide singleton, built against the selected checkpointer
(Postgres when DATABASE_URL is set, else in-memory).
"""

from __future__ import annotations

import asyncio

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import ReviveState
from app.domain.models import InvestigationStatus
from app.persistence.checkpoint import get_checkpointer

_graph = None
_lock = asyncio.Lock()


def _after_resolve(state: ReviveState) -> str:
    return "end" if state.get("status") is InvestigationStatus.FAILED else "collect"


def _build(checkpointer):
    g = StateGraph(ReviveState)

    g.add_node("resolve_customer", nodes.resolve_customer)
    g.add_node("collect_evidence", nodes.collect_evidence)
    g.add_node("normalize_evidence", nodes.normalize_evidence)
    g.add_node("diagnose", nodes.diagnose)
    g.add_node("assess_recoverability", nodes.assess_recoverability)
    g.add_node("select_intervention", nodes.select_intervention)
    g.add_node("plan_actions", nodes.plan_actions)
    g.add_node("approval", nodes.approval)
    g.add_node("execute_actions", nodes.execute_actions)
    g.add_node("verify_actions", nodes.verify_actions)
    g.add_node("finalize", nodes.finalize)

    g.add_edge(START, "resolve_customer")
    g.add_conditional_edges(
        "resolve_customer",
        _after_resolve,
        {"collect": "collect_evidence", "end": END},
    )
    g.add_edge("collect_evidence", "normalize_evidence")
    g.add_edge("normalize_evidence", "diagnose")
    g.add_edge("diagnose", "assess_recoverability")
    g.add_edge("assess_recoverability", "select_intervention")
    g.add_edge("select_intervention", "plan_actions")
    g.add_edge("plan_actions", "approval")
    g.add_edge("approval", "execute_actions")
    g.add_edge("execute_actions", "verify_actions")
    g.add_edge("verify_actions", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer)


async def get_graph():
    global _graph
    async with _lock:
        if _graph is None:
            checkpointer = await get_checkpointer()
            _graph = _build(checkpointer)
        return _graph


async def reset_graph() -> None:
    """Drop the cached graph. Used by tests for isolation."""
    global _graph
    _graph = None
