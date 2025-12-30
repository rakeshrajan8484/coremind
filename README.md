🧠 CoreMind Architecture Contract — v2 (Authoritative)

Purpose
CoreMind is a deterministic, agentic system that converts natural language into validated objectives, resolves ambiguity through identity discovery, and executes actions through strictly governed tools.

This contract defines roles, data shapes, allowed transitions, and failure behavior.

1️⃣ SYSTEM ROLES (NON-NEGOTIABLE)
ATLAS — Planner

Responsibilities

Convert user intent into a single Objective

Validate Objective against registered ObjectiveSpecs

Decide when identity resolution is required

NEVER execute tools

NEVER guess missing data

Forbidden

Tool calls

Execution logic

Semantic heuristics

Silent retries

Action inference

NEMESIS — Executor

Responsibilities

Execute a validated Objective

Choose tools deterministically

Enforce tool-call safety

Produce execution artifacts

Forbidden

Planning

Reinterpreting objectives

Creating objectives

Asking questions

IRIS — Reference Resolver

Responsibilities

Resolve natural-language references to concrete IDs

Choose from provided candidates only

Return structured resolution output

Forbidden

Tool calls

Planning

Execution

Asking follow-ups

2️⃣ OBJECTIVE (CORE DATA CONTRACT)

An Objective describes what must change, not how.

Objective Shape (Canonical)
{
  "domain": "<string>",
  "intent": "<string>",
  "target": {
    "entity": "<string>",
    "selector": "single | subset | all",
    "filter": {}
  },
  "operation": {
    "type": "<string>",
    "value": "<string>"
  },
  "constraints": null | {}
}

3️⃣ OBJECTIVE SPECS (CAPABILITY DECLARATION)

ObjectiveSpecs are the ONLY place where system capabilities are defined.

ObjectiveSpec Fields
ObjectiveSpec(
    domain: str,
    intent: str,
    description: str,

    allowed_selectors: list[str],
    required_filter_fields: dict[str, list[str]],

    operation_type: str,
    allowed_operation_values: list[str],

    requires_concrete_identity: bool,
)

Example: Update Read State
UPDATE_READ_STATE = ObjectiveSpec(
    domain="email",
    intent="update_read_state",
    description="Mark email messages as read or unread",

    allowed_selectors=["all", "single", "subset"],
    required_filter_fields={
        "single": ["id"],
        "subset": [],
        "all": [],
    },

    operation_type="read_state",
    allowed_operation_values=["read", "unread"],

    requires_concrete_identity=True,
)

Example: Delete Message
DELETE_MESSAGE = ObjectiveSpec(
    domain="email",
    intent="delete_message",
    description="Delete email messages",

    allowed_selectors=["single", "subset"],
    required_filter_fields={
        "single": ["id"],
        "subset": [],
    },

    operation_type="delete",
    allowed_operation_values=["message"],

    requires_concrete_identity=True,
)

4️⃣ PLANNER PROMPT CONTRACT (ATLAS)

The planner may ONLY emit objectives that exist in the ObjectiveSpec registry.

Capability Declaration Rule

Every supported intent MUST be declared explicitly in the planner prompt.

Example (Email domain):

DOMAIN KNOWLEDGE — EMAIL

- "mark as read" → intent = "update_read_state"
- "mark as unread" → intent = "update_read_state"
- "delete", "remove", "trash" → intent = "delete_message"

IMPORTANT:
- Deleting is NOT the same as marking unread
- If a concrete ID is missing, leave target.filter empty

Planner Output Rules

Output ONLY valid JSON or null

NEVER invent IDs

NEVER invent filters

If reference is ambiguous → leave filter empty

If objective cannot be formed → return null

5️⃣ VALIDATION & ESCALATION RULES (ATLAS)
Validation Outcomes
Condition	Action
Objective valid	Send to NEMESIS
Missing identity & requires_concrete_identity	Escalate to retrieval
Unsupported intent	User-facing rejection
Invalid shape	User clarification
Retrieval Escalation (STRICT)

When identity is missing:

{
  "domain": "entity",
  "intent": "retrieve_candidates",
  "target": {
    "entity": "<same entity>",
    "selector": "subset",
    "filter": {}
  },
  "operation": {
    "type": "retrieve",
    "value": "candidates"
  },
  "constraints": {
    "limit": 10
  }
}


🔒 Retrieval never invents actions
🔒 Retrieval never modifies intent

6️⃣ DISCOVERY RULES (IMPORTANT)
Discovery is NOT planning.

Discovery exists only to:

Fetch candidates

Resolve references

Return IDs

Discovery MUST NOT:

Create new intents

Modify intent semantics

Decide actions

Guess operations

7️⃣ IRIS CONTRACT
Input
{
  "reference": "<string>",
  "candidates": [
    { "id": "<string>", "label": "<string>", "source": "<string|null>" }
  ]
}

Output (One Only)

Single

{ "resolution": "single", "id": "<id>", "confidence": 0.0 }


Ambiguous

{ "resolution": "ambiguous", "candidates": [...], "confidence": 0.0 }


None

{ "resolution": "none", "confidence": 0.0 }

8️⃣ EXECUTION RULES (NEMESIS)

One tool call per step

Never repeat a tool

Never infer missing data

Never reinterpret intent

Never change objective

Allowed Step Output
{ "type": "tool", "tool": "<tool_name>", "args": {} }

{ "type": "done", "summary": "<string>" }

9️⃣ LANGUAGE & FORMAT SAFETY

System language: English

Output JSON keys must be canonical English

Non-English keys must be normalized or rejected

Any invalid step → hard failure

🔚 FINAL GUARANTEES

This contract ensures:

No hardcoded flows

No semantic drift

No planner hallucination

No executor guessing

Deterministic recovery paths

Safe irreversible actions (delete)