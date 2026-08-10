"""
Auto-generated tool: send_message_to_channel
Post a message to a Slack channel (stub).
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Any


class send_message_to_channelSchema(BaseModel):
    message: Any = Field(description="")


class send_message_to_channel(BaseTool):
    name: str = "send_message_to_channel"
    description: str = """Post a message to a Slack channel (stub)."""
    args_schema: Type[BaseModel] = send_message_to_channelSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.send_message_to_channel

        Implemented to mirror the original stub behavior: print the message.
        """
        message = kwargs.get("message", "")
        print(f"[Slack] {message}")
        return "ok"
