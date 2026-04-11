"""
Auto-generated Pydantic models for structured outputs.
"""

from typing import Optional
from pydantic import BaseModel


class ResearchOutline(BaseModel):
    title: str
    key_claims: str
    sources: str


class FinalPaper(BaseModel):
    abstract: str
    body_paragraphs: str
    conclusion: str
