from coremind.graph.validate import validate_plan

def validate_node(state):
    validate_plan(state.plan)
    return {"next_node": "IRIS"}
