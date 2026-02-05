from .spec import ObjectiveSpec

# =================================================
# EMAIL DOMAIN
# =================================================

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

    allowed_selectors=["single"],
    required_filter_fields={
        "single": [],
    },

    operation_type="read",
    allowed_operation_values=["content"],

    requires_concrete_identity=True,
)

# -------------------------------------------------
# COMPOSE MESSAGE (CREATE DRAFT)
# -------------------------------------------------

COMPOSE_MESSAGE = ObjectiveSpec(
    domain="email",
    intent="compose_message",
    description="Compose a new email draft",

    allowed_selectors=["new"],
    required_filter_fields={
        "new": [],
    },

    operation_type="create",
    allowed_operation_values=["email_draft"],

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
# DELETE BULK MESSAGES
# -------------------------------------------------

DELETE_BULK_MESSAGES = ObjectiveSpec(
    domain="email",
    intent="delete_messages_bulk",
    description="Delete multiple email messages by their IDs",

    allowed_selectors=["subset"],
    required_filter_fields={
        "subset": ["ids"],
    },

    operation_type="delete",
    allowed_operation_values=["bulk_messages"],

    requires_concrete_identity=False,
)

# =================================================
# SMART HOME DOMAIN (NEW — HARD-LOCKED)
# =================================================

# -------------------------------------------------
# SWITCH POWER (ON / OFF / TOGGLE)
# -------------------------------------------------

SWITCH_POWER = ObjectiveSpec(
    domain="smart_home",
    intent="switch_power",
    description="Explicitly switch power state of a smart device or device group",

    # 🔒 ONLY explicit selector allowed
    allowed_selectors=["explicit"],

    # 🔒 NO filters allowed (no discovery, no inference)
    required_filter_fields={
        "explicit": [],
    },

    operation_type="power",
    allowed_operation_values=["on", "off", "toggle"],

    # 🔒 Explicit device binding is enforced in NEMESIS
    requires_concrete_identity=False,
)

# =================================================
# OBJECTIVE REGISTRY
# =================================================

OBJECTIVE_REGISTRY = {
    # EMAIL
    ("email", "update_read_state"): UPDATE_READ_STATE,
    ("email", "delete_message"): DELETE_MESSAGE,
    ("email", "summarize"): SUMMARIZE_MESSAGE,
    ("email", "compose_message"): COMPOSE_MESSAGE,
    ("email", "send_message"): SEND_MESSAGE,
    ("email", "send_draft"): SEND_DRAFT,
    ("email", "delete_messages_bulk"): DELETE_BULK_MESSAGES,

    # DISCOVERY
    ("entity", "retrieve_candidates"): RETRIEVE_CANDIDATES,

    # SMART HOME
    ("smart_home", "switch_power"): SWITCH_POWER,
}
