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