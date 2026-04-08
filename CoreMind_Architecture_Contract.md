# CoreMind Architecture Contract (v1.1)
## With ARGUS Observer Agent

---

## CoreMind

A **contract-driven, multi-agent execution system** designed to safely translate natural language into real-world side effects (email actions today, extensible to other domains tomorrow).

This document is the **normative architectural contract** of CoreMind.  
Any behavior not described here is considered undefined.

---

## 1. Core Design Principles

### 1.1 Determinism over eloquence

LLMs are used **only where ambiguity exists** (intent understanding, planning, diagnosis).
All irreversible actions and confirmations are rendered **deterministically in code**.

### 1.2 Contract-first architecture

Every agent has a strict, enforceable contract.
Violations are treated as **bugs**, not prompt-tuning issues.

### 1.3 Separation of concerns

Language understanding, execution, validation, and observation are **intentionally split**.

---

## 2. High-Level Architecture

### Execution Plane

```
User
  │
  ▼
ATLAS (Planner & UX)
  │
  ▼
NEMESIS (Executor)
  │
  ▼
TOOLS (Side effects)
```

### Observability Plane (Non-blocking)

```
Execution Graph
   │
   ▼
ARGUS (Observer & Forensics)
```

ARGUS operates **out-of-band** and has no authority over execution.

---

## 3. Agent Responsibilities (Hard Contract)

### 3.1 ATLAS — Planner & User Interface

**Responsibilities**
- Interpret user intent using LLMs
- Compile objectives (single or multi-step)
- Own *all* user-facing language
- Decide when execution terminates
- Render confirmations using deterministic templates

**Prohibitions**
- Must not execute tools
- Must not perform side effects
- Must not infer execution results

---

### 3.2 NEMESIS — Execution Engine

**Responsibilities**
- Execute exactly one objective
- Call tools deterministically
- Enforce execution invariants
- Honor `force_done` termination

**Output Schema**
```json
{
  "status": "success" | "error",
  "artifacts": {
    "raw_data": {}
  }
}
```

**Prohibitions**
- Must not speak to the user
- Must not plan objectives
- Must not resolve ambiguity
- Must not retry implicitly

---

### 3.3 TOOLS — Side Effects Only

**Responsibilities**
- Perform irreversible actions
- Return raw execution data
- Signal completion via `force_done`

**Prohibitions**
- Must not format user messages
- Must not control flow

---

### 3.4 IRIS — Reference Resolution (Optional)

**Responsibilities**
- Resolve ambiguous references deterministically
- Map natural language to concrete IDs

**Prohibitions**
- Must not invent IDs
- Must not execute tools
- Must not speak to user

---

### 3.5 ARGUS — Observer & Forensics Agent

ARGUS is a **read-only diagnostic agent**.

**Responsibilities**
- Analyze logs, traces, and failures using an LLM
- Detect contract violations and anomalies
- Classify failures
- Emit structured diagnostic reports

**Prohibitions (Absolute)**
- Must not execute tools
- Must not modify objectives
- Must not rewrite prompts or artifacts
- Must not communicate with users
- Must not influence live execution
- Must not trigger retries or loops

---

### ARGUS Output Contract

```json
{
  "status": "ok" | "failure",
  "failure_class": "schema_violation | contract_violation | tool_error | ambiguity | unknown",
  "root_cause": "string",
  "confidence": 0.0,
  "evidence": ["string"],
  "recommended_action": {
    "action_type": "request_input | block_execution | investigate",
    "reason": "string"
  },
  "rewrite_hint": {
    "artifact": "prompt | schema | validator",
    "intent": "string",
    "constraints": ["string"]
  }
}
```

ARGUS outputs are **advisory only**.

---

## 4. Execution Invariants

### 4.1 Single execution per tool
A tool may be called **at most once per objective**.

### 4.2 Deterministic termination
If a tool returns:
```json
{ "force_done": true }
```
NEMESIS must terminate immediately.

### 4.3 No LLM-dependent execution
Execution correctness must not depend on LLM obedience.

### 4.4 No user-facing language outside ATLAS
All communication is owned by ATLAS.

### 4.5 Observability must be non-intrusive
- ARGUS must not block execution
- ARGUS failure must not cascade

### 4.6 No self-modification at runtime
- No agent may rewrite prompts or schemas during execution
- All changes must be explicit and versioned

---

## 5. Deterministic Confirmations

All destructive or irreversible actions use **schema-driven templates**.
LLM summaries are forbidden.

---

## 6. Model Agnosticism

CoreMind is compatible with HuggingFace, Ollama, or hosted models.
It is hardened against malformed LLM outputs.

---

## 7. Example Flow (Failure Case)

1. User submits intent
2. ATLAS plans objective
3. NEMESIS executes tool
4. Tool fails
5. ATLAS reports deterministic error
6. ARGUS analyzes logs post-hoc
7. System terminates cleanly

---

## 8. Non-Goals

- Implicit retries
- Self-healing prompts
- LLM-driven execution
- Hidden control flow
- Runtime self-modification

---

## 9. Final Statement

CoreMind is intentionally **boring at execution time**.

> Intelligence proposes.  
> Governance decides.  
> Execution obeys.

This document is the architectural contract.
