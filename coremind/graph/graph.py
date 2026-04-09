from langgraph.graph import StateGraph, END
from coremind.agents.atlas.node import atlas_node
from coremind.agents.nemesis.node import make_nemesis_node
from coremind.agents.nexis.node import make_nexis_node  # 🆕
from coremind.agents.iris.resolver import iris_node


def route_from_atlas(state: dict):
    if state.get("terminated"):
        return END

    obj = state.get("objective")

    if obj:
        # 🆕 NEXIS routing
        if obj.get("domain", "").lower() == "code":
            constraints = obj.get("constraints", {})
            # 🔥 If path is missing or invalid → go to IRIS
            path = constraints.get("path")

            if not path or "." not in path:
                return "iris"

            return "nexis"

        target = obj.get("target", {})
        filt = target.get("filter", {})

        if (
            state.get("needs_reference_resolution")
            and not filt
            and not obj.get("_resolution_ambiguous")
        ):
            return "iris"

        return "nemesis"

    if state.get("objective_queue"):
        return "atlas"

    return END


def route_from_nemesis(state: dict):
    return "atlas"


def route_from_iris(state: dict):
    return "atlas"




def route_from_nexis(state: dict):
    return "atlas"


def build_graph():
    graph = StateGraph(dict)

    graph.add_node("atlas", atlas_node)
    graph.add_node("nemesis", make_nemesis_node())
    graph.add_node("nexis", make_nexis_node())
    graph.add_node("iris", iris_node)
    graph.set_entry_point("atlas")

    graph.add_conditional_edges(
        "atlas",
        route_from_atlas,
        {
            "atlas": "atlas",
            "nexis": "nexis",
            "nemesis": "nemesis",
            "iris": "iris",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "nexis",
        route_from_nexis,
        {"atlas": "atlas"},
    )

    graph.add_conditional_edges(
        "nemesis",
        route_from_nemesis,
        {"atlas": "atlas"},
    )

    graph.add_conditional_edges(
        "iris",
        route_from_iris,
        {"atlas": "atlas"},
    )

    return graph.compile()