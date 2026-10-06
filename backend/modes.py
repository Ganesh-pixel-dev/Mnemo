import re

_ELABORATION = re.compile(
    r"\b(explain|explains|explaining|elaborate|elaboration|elaborately|example|examples|"
    r"why|intuition|simplify|walk me through|in detail|more detail|more details|"
    r"tell me more|more about|beyond)\b"
    r"|\bhow\b(?!\s+(many|much|long|old|often|far|big|large|tall)\b)",
    re.IGNORECASE,
)

RECALL = "Recall"
ELABORATION = "Elaboration"


def detect_mode(query: str) -> str:
    return ELABORATION if _ELABORATION.search(query) else RECALL
