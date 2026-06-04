"""Stub side-effect helpers for the LangGraph meeting-assistant port."""


def save_tasks_to_trello(tasks: list[dict]) -> None:
    """Push each task to a Trello board (stub)."""
    for t in tasks:
        print(f"[Trello] {t.get('name', '')}: {t.get('description', '')}")


def send_message_to_channel(message: str) -> None:
    """Post a message to a Slack channel (stub)."""
    print(f"[Slack] {message}")
