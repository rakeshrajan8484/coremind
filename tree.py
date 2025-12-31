from pathlib import Path

EXCLUDE_DIRS = {
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
}

def generate_tree(path: Path, prefix: str = ""):
    entries = sorted(
        [p for p in path.iterdir() if p.name not in EXCLUDE_DIRS],
        key=lambda p: (p.is_file(), p.name.lower()),
    )

    for index, entry in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = "└── " if is_last else "├── "
        print(prefix + connector + entry.name)

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            generate_tree(entry, prefix + extension)

if __name__ == "__main__":
    root = Path(".")
    print(".")
    generate_tree(root)

# python tree.py > structure.md
# uv run python -m tree.py > structure.md