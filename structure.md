User
 ↓
ATLAS (conversation + planning)
 ↓ objective
NEMESIS (LLM execution agent)
 ↓ tool calls
TOOLS (Gmail, etc.)
 ↓ observations
NEMESIS (decides: next tool OR done)
 ↓ result
ATLAS (final response to user)

          ↑
          |
        IRIS
 (reference resolution service)


 | Component     | Owns                                                                                | Does NOT Own                            |
| ------------- | ----------------------------------------------------------------------------------- | --------------------------------------- |
| **ATLAS**     | Conversation, intent understanding, clarification, objective lifecycle, termination | Tool execution, low-level API reasoning |
| **NEMESIS**   | Tool selection, argument selection, execution loops, completion judgment            | User interaction, clarification         |
| **TOOLS**     | API calls, schemas, side effects                                                    | Reasoning                               |
| **IRIS**      | Reference resolution, entity disambiguation                                         | Planning, execution, looping            |
| **LangGraph** | Control flow                                                                        | Intelligence                            |


Final, contradiction-free mental model (lock this in)
Agents (autonomous, looping, decision-making)

ATLAS

NEMESIS

Cognitive Services (stateless, callable, no loops)

IRIS

Execution Primitives

Tools

Infrastructure

LangGraph

LLMFactory