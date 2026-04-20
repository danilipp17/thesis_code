"""
Auto-generated Pydantic models for structured outputs.
"""

from typing import Optional
from pydantic import BaseModel


class FinalPaper(BaseModel):
    abstract: str
    body_paragraphs: str
    conclusion: str


class ResearchOutline(BaseModel):
    title: str
    key_claims: str
    sources: str
