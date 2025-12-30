from langchain_core.messages import HumanMessage

from coremind.graph.graph import build_graph
from coremind.state import CoreMindState


def main():
    # Build LangGraph app
    app = build_graph()

    # Initialize state with a HumanMessage (MANDATORY)
    initial_state = CoreMindState(
        messages=[
            HumanMessage(
                content="Delete the email from Adobe Express"
            )
        ]
    )

    # Run the graph
    final_state = app.invoke(initial_state)

    # Print final assistant response
    print("FINAL STATE:")
    print(final_state)

    print("\nASSISTANT RESPONSE:")
    messages = final_state.get("messages", [])
    if messages:
        print(messages[-1].content)
    else:
        print("No assistant message produced.")

if __name__ == "__main__":
    main()
