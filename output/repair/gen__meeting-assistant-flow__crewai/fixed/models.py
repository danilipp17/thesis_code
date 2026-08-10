"""
Auto-generated Pydantic models for structured outputs.
"""

from typing import List
from pydantic import BaseModel


class MeetingTask(BaseModel):
    name: str
    description: str


class MeetingTaskList(BaseModel):
    tasks: List[MeetingTask]
