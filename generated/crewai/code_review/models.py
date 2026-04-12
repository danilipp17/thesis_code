"""
Auto-generated Pydantic models for structured outputs.
"""

from typing import Optional
from pydantic import BaseModel


class ReviewResult(BaseModel):
    approved: bool
    summary: str
    critical_count: int
    action_items: str
