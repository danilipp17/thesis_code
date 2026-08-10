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
    """
    # Accept either a JSON string or a Python list/dict structure.
    task_list = []
    try:
        if isinstance(tasks, str):
            task_list = json.loads(tasks)
        elif isinstance(tasks, dict):
            # single task dict
            task_list = [tasks]
        elif isinstance(tasks, (list, tuple)):
            task_list = list(tasks)
        else:
            task_list = [str(tasks)]
    except Exception:
        task_list = [str(tasks)]

    for t in task_list:
        if isinstance(t, dict):
            name = t.get("name", "")
            desc = t.get("description", "")
        else:
            name = str(t)
            desc = ""
        print(f"[Trello] {name}: {desc}")
    return "saved"

@tool
def send_message_to_channel(message: str) -> str:
    """send_message_to_channel
    Post a message to a Slack channel (stub).
    """
    print(f"[Slack] {message}")
    return "sent"
