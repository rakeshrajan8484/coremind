import os
from typing import Optional


def safe_path(root: str, relative_path: str) -> str:
    root_abs = os.path.abspath(root)
    full_path = os.path.abspath(os.path.join(root_abs, relative_path))

    if not full_path.startswith(root_abs):
        raise Exception("Path traversal detected")

    return full_path


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def write_file(root: str, relative_path: str, content: str) -> str:
    full_path = safe_path(root, relative_path)

    directory = os.path.dirname(full_path)
    ensure_dir(directory)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path


def read_file(root: str, relative_path: str) -> str:
    full_path = safe_path(root, relative_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"{relative_path} not found")

    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def append_file(root: str, relative_path: str, content: str) -> str:
    full_path = safe_path(root, relative_path)

    with open(full_path, "a", encoding="utf-8") as f:
        f.write(content)

    return full_path


def delete_file(root: str, relative_path: str) -> bool:
    full_path = safe_path(root, relative_path)

    if os.path.exists(full_path):
        os.remove(full_path)
        return True

    return False


def list_dir(root: str, relative_path: Optional[str] = ""):
    full_path = safe_path(root, relative_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"{relative_path} not found")

    return os.listdir(full_path)

