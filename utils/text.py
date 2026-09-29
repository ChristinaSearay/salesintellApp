"""Small wording helpers for rep-facing copy."""


def count_noun(count: int, noun: str) -> str:
    """'1 order', '3 orders' — never '1 orders'."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
