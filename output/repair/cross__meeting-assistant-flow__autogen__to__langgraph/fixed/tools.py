"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool
import json
from typing import Any

@tool
def save_tasks_to_trello(tasks: Any) -> str:
    """save_tasks_to_trello
    Push each task to a Trello board (stub).
    Accepts either a JSON string or a Python list of dicts.
    """
    # Normalize input into a list of dicts
    ts = []
    try:
        if isinstance(tasks, str):
            ts = json.loads(tasks)
        elif isinstance(tasks, (list, tuple)):
            ts = list(tasks)
        else:
            ts = [tasks]
    except Exception:
        ts = []

    for t in ts:
        # tolerate non-dict entries
        name = t.get("name", "") if isinstance(t, dict) else str(t)
        desc = t.get("description", "") if isinstance(t, dict) else ""
        print(f"[Trello] {name}: {desc}")
    return "ok"


@tool
def send_message_to_channel(message: str) -> str:
    """send_message_to_channel
    Post a message to a Slack channel (stub).
    """
    print(f"[Slack] {message}")
    return "ok"
