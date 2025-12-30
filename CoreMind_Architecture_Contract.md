# CoreMind Architecture Contract (v1.0)

## Purpose
CoreMind is a multi-agent system designed to strictly separate:
- conversation
- planning
- execution
- reference resolution
- infrastructure

This document is **authoritative**. Any deviation is a bug.

---

## 1. Core Components

### 1.1 ATLAS — Conversational Planner Agent
**Role:** Primary interface to the user.

**Responsibilities**
- Talk to the user
- Ask clarifying questions
- Interpret intent, constraints, and context
- Decide *what objective should be attempted next*
- Own the objective lifecycle
- Decide when the system terminates
- Invoke IRIS when human references must be resolved

**Must NOT**
- Call tools
- Execute side effects
- Choose API-level parameters
- Loop over execution steps

**LLM**
- `LLMFactory.atlas()`

---

### 1.2 NEMESIS — Execution Agent
**Role:** Autonomous execution agent.

**Responsibilities**
- Receive an objective from ATLAS
- Use its own LLM to:
  - choose the correct tool
  - choose tool arguments
  - reason over past observations
  - avoid repeated tool calls
- Execute tools
- Decide whether the objective is complete
- Return structured results to ATLAS

**Must NOT**
- Talk to the user
- Ask clarifying questions
- Resolve ambiguous references
- Own objective lifecycle beyond execution

**LLM**
- `LLMFactory.nemesis()`

---

### 1.3 TOOLS — Execution Primitives
**Role:** Perform real-world side effects.

**Responsibilities**
- Execute APIs (Gmail, etc.)
- Validate inputs via schemas
- Return structured outputs

**Must NOT**
- Reason
- Choose when to run
- Maintain state
- Call other tools

---

### 1.4 IRIS — Reference Resolution Service
**Role:** Resolve human references into concrete entities.

**Responsibilities**
- Resolve phrases like:
  - “the LinkedIn email”
  - “the second one”
  - “that message”
- Return:
  - single resolution
  - ambiguous
  - none

**Must NOT**
- Call tools
- Loop
- Decide objectives
- Execute side effects
- Talk to the user

**LLM**
- `LLMFactory.iris()`

> IRIS has an LLM but is **not an agent**.
> It is a stateless cognitive service.

---

### 1.5 LangGraph — Control Flow Infrastructure
**Role:** Deterministic orchestration.

**Responsibilities**
- Route execution between ATLAS and NEMESIS
- Maintain state as a dict
- Enforce termination

**Must NOT**
- Contain intelligence
- Make decisions

---

## 2. State Contract

State is always a dict:

```python
state = {
  "messages": list,
  "current_agent": "atlas" | "nemesis",
  "objective": dict | None,
  "result": dict | None,
  "terminated": bool,
}
```

Rules:
- No attribute access (`state.foo` forbidden)
- ATLAS creates and clears objectives
- NEMESIS writes results
- ATLAS consumes results

---

## 3. Canonical Execution Flow

User  
↓  
ATLAS (conversation & planning)  
↓ objective  
NEMESIS (LLM-driven execution)  
↓ tool calls  
TOOLS  
↓ observations  
NEMESIS (decide next tool or done)  
↓ result  
ATLAS (final response)

IRIS is invoked by ATLAS only at reference-resolution boundaries.

---

## 4. LLM Usage Rules

| Component | Purpose | Agentic |
|---------|--------|--------|
| ATLAS | Planning & conversation | Yes |
| NEMESIS | Tool selection & execution reasoning | Yes |
| IRIS | Reference resolution | No |

---

## 5. Valid Folder Structure

```text
coremind/
├── main.py
├── graph.py
├── state.py
│
├── llms/
│   └── factory.py
│
├── agents/
│   ├── atlas/
│   │   ├── node.py
│   │   ├── parser.py
│   │   └── prompt.py
│   │
│   └── nemesis/
│       ├── node.py
│       ├── agent.py          # execution loop (LLM-driven)
│       ├── prompt.py
│       └── tools/
│           ├── gmail/
│           │   ├── check_unread.py
│           │   ├── get_email_content.py
│           │   ├── delete_email.py
│           │   └── mark_email.py
│           ├── registry.py
│           └── __init__.py
│
├── services/
│   └── iris/
│       ├── resolver.py
│       └── prompt.py
│
└── pyproject.toml
```

Folder location defines **ownership**, not intelligence.

---

## 6. Non-Negotiable Invariants

- ATLAS never calls tools
- NEMESIS never talks to the user
- IRIS never loops or executes
- Tools never reason
- Objectives must never contain raw natural language
- Execution intelligence lives in NEMESIS
- Conversation intelligence lives in ATLAS

---

## 7. Final Principle

> Conversation plans. Execution reasons. Tools act.  
> Services resolve. Infrastructure routes.

If this sentence is violated, CoreMind is broken.

---
End of Contract
