# CoreMind

A **contract-driven, multi-agent execution system** designed to safely translate natural language into real-world side effects (email actions today, extensible to other domains tomorrow).

This README documents the **final, stabilized architecture and invariants** we arrived at after hardening the system against LLM nondeterminism, hallucinations, and execution loops.

---

## 1. Core Design Principles

### 1.1 Determinism over eloquence

LLMs are used **only where ambiguity exists** (intent understanding, planning). All irreversible actions and confirmations are rendered **deterministically in code**.

### 1.2 Contract-first architecture

Every agent has a strict, enforceable contract. Violations are treated as bugs, not prompt-tuning issues.

### 1.3 Separation of concerns

Language understanding, execution, and user communication are **intentionally split**.

---

## 2. High-Level Architecture

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

Optional supporting component:

```
IRIS (Reference Resolver)
```

---

## 3. Agent Responsibilities (Hard Contract)

### 3.1 ATLAS — Planner & User Interface

**What ATLAS does:**

* Interprets user intent via LLM
* Plans objectives (single or multi-step)
* Owns *all* user-facing language
* Decides when the graph terminates
* Converts raw execution artifacts into human-readable confirmations

**What ATLAS must never do:**

* Execute tools
* Perform side effects
* Infer execution results

---

### 3.2 NEMESIS — Execution Engine

**What NEMESIS does:**

* Executes exactly one objective
* Calls tools deterministically
* Enforces execution invariants
* Detects termination signals (`force_done`)

**What NEMESIS must never do:**

* Speak to the user
* Generate summaries or explanations
* Ask questions
* Plan objectives
* Resolve semantic ambiguity

**Nemesis output schema:**

```json
{
  "status": "success" | "error",
  "artifacts": {
    "raw_data": { "..." }
  }
}
```

---

### 3.3 TOOLS — Side Effects Only

**What tools do:**

* Perform irreversible actions (delete, send, modify)
* Return raw execution data
* Signal completion via `force_done` when appropriate

**What tools must never do:**

* Format user messages
* Decide flow control

---

### 3.4 IRIS — Reference Resolution (Optional)

**Purpose:**

* Resolve ambiguous natural language references ("that email", "the LinkedIn mail")
* Deterministically map to concrete IDs

**Strict constraints:**

* Never invent IDs
* Never execute tools
* Never speak to user

---

## 4. Execution Invariants (Critical)

These rules are enforced in code, not prompts.

### 4.1 Single execution per tool

A tool may be called **at most once per objective**.

### 4.2 Deterministic termination

If a tool returns:

```json
{"force_done": true}
```

NEMESIS must **terminate immediately** and return control to ATLAS.

### 4.3 No LLM-dependent execution

* LLMs may *suggest* a tool
* Execution must not depend on LLM obedience
* Fallback routing is deterministic

### 4.4 No user-facing language outside ATLAS

All confirmations, summaries, and explanations are authored **only** in ATLAS.

---

## 5. Why Summaries Are Deterministic (By Design)

For destructive or irreversible actions (delete, send, modify):

* LLM summaries are unsafe
* Nondeterminism is unacceptable
* Numeric ground truth must be preserved

Therefore, ATLAS renders confirmations via **schema-driven templates**.

---

## 6. HuggingFace vs Ollama Compatibility

The system is **model-agnostic by design**.

Hardened against:

* Prose + JSON outputs
* Multiple JSON blocks
* Echoed objectives
* Hallucinated execution results

---

## 7. Typical End-to-End Flow (Bulk Delete Example)

1. **User:** "Delete all mails from LinkedIn"
2. **ATLAS:** Plans `delete_messages_bulk`
3. **NEMESIS:** Executes `delete_emails_bulk`
4. **Tool:** Deletes emails, returns `{ deleted: N, force_done: true }`
5. **ATLAS:** Responds: *"I’ve deleted N emails from LinkedIn."*
6. **Graph terminates**

No loops. No hallucinations. No ambiguity.

---

# =======================
# ADDITIVE EXTENSIONS
# =======================

## 8. Observation & Perception Domains (Additive)

CoreMind supports **non-terminal observation objectives** such as:

* Live camera feeds
* Audio streams
* Sensor monitoring

These objectives differ fundamentally from action objectives.

### Properties

* They do NOT terminate automatically
* They emit events, not final results
* They must be explicitly stopped
* They NEVER use `force_done`

---

## 9. Vision Use Case — Live Camera Watchlist Matching

**User intent:**
> "Alert me if this person appears on the camera"

### Flow

1. User uploads one or more reference photos
2. IRIS extracts deterministic face embeddings (no identity logic)
3. ATLAS creates a watchlist artifact
4. ATLAS starts a live observation objective on a video stream
5. Observation tools emit face-detected events
6. Reasoning compares embeddings against the watchlist
7. Action objectives notify the user on match
8. Observation continues until explicitly stopped

### Storage Guarantees

* Raw frames are NOT stored by default
* Frames are processed in memory and discarded
* Only events, embeddings, and governed evidence are persisted

This preserves determinism, scalability, and privacy.

---

## 10. Non-Goals (Explicit)

* ❌ Letting LLMs confirm destructive actions
* ❌ Using prompt engineering for correctness
* ❌ Mixing execution with language generation
* ❌ Implicit control flow via model output
* ❌ Storing raw video frames by default

---

## 11. Final Note

CoreMind is intentionally **boring at execution time**.

All the intelligence happens *before* execution.
Once tools run, the system behaves like a traditional, auditable program.

**This README is the architectural contract.**

## 12. Folder Structure
.
├── .coremind
│   └── gmail_credentials.json
├── coremind
│   ├── agents
│   │   ├── atlas
│   │   │   ├── __init__.py
│   │   │   ├── intent_satisfaction.py
│   │   │   ├── node.py
│   │   │   ├── objective_compiler.py
│   │   │   ├── parser.py
│   │   │   └── prompt.py
│   │   └── nemesis
│   │       ├── adapters
│   │       │   ├── documents.py
│   │       │   ├── email.py
│   │       │   ├── files.py
│   │       │   └── types.py
│   │       ├── tools
│   │       │   ├── gmail
│   │       │   │   ├── __init__.py
│   │       │   │   ├── check_unread.py
│   │       │   │   ├── delete_email.py
│   │       │   │   ├── delete_emails_bulk.py
│   │       │   │   ├── get_email_content.py
│   │       │   │   ├── list_recent_emails.py
│   │       │   │   ├── mark_all_read.py
│   │       │   │   └── mark_email.py
│   │       │   ├── __init__.py
│   │       │   └── registry.py
│   │       ├── __init__.py
│   │       ├── agent.py
│   │       ├── node.py
│   │       └── prompt.py
│   ├── api
│   │   └── server.py
│   ├── graph
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── validate.py
│   │   └── validate_node.py
│   ├── integrations
│   │   └── gmail
│   │       └── client.py
│   ├── llms
│   │   ├── __init__.py
│   │   └── factory.py
│   ├── objectives
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── spec.py
│   │   └── validate.py
│   ├── services
│   │   └── iris
│   │       ├── __init__.py
│   │       ├── prompt.py
│   │       └── resolver.py
│   ├── tools
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── schemas.py
│   │   └── utils.py
│   ├── __init__.py
│   ├── config.py
│   ├── logging.py
│   ├── main.py
│   └── state.py
├── coremind.egg-info
│   ├── dependency_links.txt
│   ├── PKG-INFO
│   ├── requires.txt
│   ├── SOURCES.txt
│   └── top_level.txt
├── tests
│   └── test_graph.py
├── .env
├── .gitattributes
├── .gitignore
├── CoreMind_Architecture_Contract.md
├── pyproject.toml
├── README.md
├── requirements.lock.txt
├── requirements.txt
├── structure.md
├── tree.py
└── uv.lock