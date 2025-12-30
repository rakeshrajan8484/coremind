from langgraph.graph import StateGraph, END

from coremind.agents.atlas.node import atlas_node
from coremind.agents.nemesis.node import make_nemesis_node
from coremind.services.iris.resolver import iris_node


# -------------------------------------------------
# 🔀 Routing logic (NO reasoning here)
# -------------------------------------------------

def route_from_atlas(state: dict):
    """
    Routing logic from ATLAS.

    Priority order:
    1. Termination
    2. Reference resolution
    3. Execution
    """

    if state.get("terminated"):
        return END

    if (
        state.get("needs_reference_resolution")
        and not state.get("resolution_ambiguous")
    ):
        return "iris"


    if state.get("objective") is not None:
        return "nemesis"

    return END



def route_from_nemesis(state: dict):
    """
    NEMESIS always returns control to ATLAS.
    """
    return "atlas"


def route_from_iris(state: dict):
    """
    IRIS never terminates.
    Always returns to ATLAS.
    """
    return "atlas"


# -------------------------------------------------
# 🧠 Graph construction
# -------------------------------------------------

def build_graph():
    graph = StateGraph(dict)

    # -------------------------
    # 🔒 Nodes
    # -------------------------
    graph.add_node("atlas", atlas_node)
    graph.add_node("nemesis", make_nemesis_node())
    graph.add_node("iris", iris_node)

    # -------------------------
    # 🔒 Entry point
    # -------------------------
    graph.set_entry_point("atlas")

    # -------------------------
    # 🔒 Conditional routing
    # -------------------------
    graph.add_conditional_edges(
        "atlas",
        route_from_atlas,
        {
            "nemesis": "nemesis",
            "iris": "iris",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "nemesis",
        route_from_nemesis,
        {
            "atlas": "atlas",
        },
    )

    graph.add_conditional_edges(
        "iris",
        route_from_iris,
        {
            "atlas": "atlas",
        },
    )

    return graph.compile()
