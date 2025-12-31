from .spec import ObjectiveSpec

# -------------------------------------------------
# UPDATE READ STATE
# -------------------------------------------------

UPDATE_READ_STATE = ObjectiveSpec(
    domain="email",
    intent="update_read_state",
    description="Change read/unread state of email messages",

    allowed_selectors=["all", "single", "subset"],
    required_filter_fields={
        "all": [],
        "subset": ["ids"],
        "single": ["id"],
    },

    operation_type="read_state",
    allowed_operation_values=["read", "unread"],

    requires_concrete_identity=True,
)

# -------------------------------------------------
# DELETE MESSAGE
# -------------------------------------------------

DELETE_MESSAGE = ObjectiveSpec(
    domain="email",
    intent="delete_message",
    description="Delete one or more email messages",

    allowed_selectors=["all", "single", "subset"],
    required_filter_fields={
        "all": [],
        "subset": ["ids"],
        "single": ["id"],
    },

    operation_type="delete",
    allowed_operation_values=["message"],

    requires_concrete_identity=True,
)

# -------------------------------------------------
# RETRIEVE CANDIDATES (DISCOVERY)
# -------------------------------------------------

RETRIEVE_CANDIDATES = ObjectiveSpec(
    domain="entity",
    intent="retrieve_candidates",
    description="Retrieve candidate entities for reference resolution",

    allowed_selectors=["subset"],
    required_filter_fields={
        "subset": [],
    },

    operation_type="retrieve",
    allowed_operation_values=["candidates"],

    requires_concrete_identity=False,
)


# -------------------------------------------------
# SUMMARIZE MESSAGE (READ-ONLY)
# -------------------------------------------------

SUMMARIZE_MESSAGE = ObjectiveSpec(
    domain="email",
    intent="summarize",
    description="Summarize the content of an email message",

    # Summarization always targets ONE resolved message
    allowed_selectors=["single"],

    # ❗ DO NOT require "id" here
    # ID is resolved later by IRIS
    required_filter_fields={
        "single": [],
    },

    operation_type="read",
    allowed_operation_values=["content"],

    # IRIS MUST resolve the message before execution
    requires_concrete_identity=True,
)


# -------------------------------------------------
# COMPOSE MESSAGE (CREATE DRAFT)
# -------------------------------------------------

COMPOSE_MESSAGE = ObjectiveSpec(
    domain="email",
    intent="compose_message",
    description="Compose a new email draft",

    # Creation → no existing entity
    allowed_selectors=["new"],
    required_filter_fields={
        "new": [],
    },

    operation_type="create",
    allowed_operation_values=["email_draft"],

    # 🔒 MUST NOT require identity
    requires_concrete_identity=False,
)

# -------------------------------------------------
# SEND MESSAGE (SEND DRAFT)
# -------------------------------------------------

SEND_MESSAGE = ObjectiveSpec(
    domain="email",
    intent="send_message",
    description="Send an existing email draft",

    allowed_selectors=["specific"],
    required_filter_fields={
        "specific": ["draft_id"],
    },

    operation_type="send",
    allowed_operation_values=["email"],

    # 🔒 draft_id is mandatory
    requires_concrete_identity=True,
)

SEND_DRAFT = ObjectiveSpec(
    domain="email",
    intent="send_draft",
    description="Send an existing drafted email",

    allowed_selectors=["single"],
    required_filter_fields={
        "single": ["draft_id"],
    },

    operation_type="send",
    allowed_operation_values=["draft"],

    requires_concrete_identity=True,
)

# -------------------------------------------------
# OBJECTIVE REGISTRY
# -------------------------------------------------

OBJECTIVE_REGISTRY = {
    ("email", "update_read_state"): UPDATE_READ_STATE,
    ("email", "delete_message"): DELETE_MESSAGE,
    ("email", "summarize"): SUMMARIZE_MESSAGE,
    ("entity", "retrieve_candidates"): RETRIEVE_CANDIDATES,
    ("email", "compose_message"): COMPOSE_MESSAGE,
    ("email", "send_message"): SEND_MESSAGE,
    ("email", "send_draft"): SEND_DRAFT,
}
