# from langchain_core.messages import HumanMessage

# from coremind.graph.graph import build_graph
# from coremind.state import CoreMindState


# def main():
#     # Build LangGraph app
#     app = build_graph()

#     # Initialize state with a HumanMessage (MANDATORY)
#     initial_state = CoreMindState(
#         messages=[
#             HumanMessage(
#                 content="send the email drafted"
#             )
#         ]
#     )

#     # Run the graph
#     final_state = app.invoke(initial_state)

#     # Print final assistant response
#     print("FINAL STATE:")
#     print(final_state)

#     print("\nASSISTANT RESPONSE:")
#     messages = final_state.get("messages", [])
#     if messages:
#         print(messages[-1].content)
#     else:
#         print("No assistant message produced.")

# if __name__ == "__main__":
#     main()



# coremind/main.py

import uvicorn

def main():
    uvicorn.run(
        "coremind.server.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

if __name__ == "__main__":
    main()
