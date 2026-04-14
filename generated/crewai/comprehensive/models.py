"""
Auto-generated Pydantic models for structured outputs.
"""

from typing import Optional
from pydantic import BaseModel


class AnalysisOutput(BaseModel):
    findings: str
    confidence_score: float
