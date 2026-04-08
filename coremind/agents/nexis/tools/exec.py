from typing import Tuple


def replace_text(original: str, old: str, new: str) -> str:
    if old not in original:
        raise ValueError("Target text not found for replacement")

    return original.replace(old, new)


def insert_after(original: str, target: str, new_content: str) -> str:
    if target not in original:
        raise ValueError("Target text not found")

    return original.replace(target, target + "\n" + new_content)


def insert_before(original: str, target: str, new_content: str) -> str:
    if target not in original:
        raise ValueError("Target text not found")

    return original.replace(target, new_content + "\n" + target)


def append_end(original: str, new_content: str) -> str:
    return original + "\n" + new_content


def diff_summary(old: str, new: str) -> Tuple[int, int]:
    old_lines = len(old.splitlines())
    new_lines = len(new.splitlines())

    return old_lines, new_lines

