"""
Auto-generated tool: save_tasks_to_trello
Push each task to a Trello board (stub).
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Any


class save_tasks_to_trelloSchema(BaseModel):
    tasks: Any = Field(description="")


class save_tasks_to_trello(BaseTool):
    name: str = "save_tasks_to_trello"
    description: str = """Push each task to a Trello board (stub)."""
    args_schema: Type[BaseModel] = save_tasks_to_trelloSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.save_tasks_to_trello

        Implemented to mirror the original stub behavior: print each task.
        """
        tasks = kwargs.get("tasks", [])
        # If the incoming tasks is a JSON string, try to parse it
        import json
        if isinstance(tasks, str):
            try:
                tasks = json.loads(tasks)
            except Exception:
                # keep as-is (will likely be a single string); wrap into list
                tasks = [{"name": "", "description": tasks}]
        if not isinstance(tasks, (list, tuple)):
            tasks = [tasks]
        for t in tasks:
            try:
                name = t.get("name", "") if isinstance(t, dict) else str(t)
                desc = t.get("description", "") if isinstance(t, dict) else ""
                print(f"[Trello] {name}: {desc}")
            except Exception:
                print(f"[Trello] {t}")
        return "ok"
