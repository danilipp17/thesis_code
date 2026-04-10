from pydantic import BaseModel, Field
from typing import List

class ResearchOutline(BaseModel):
    title: str = Field(..., description="The title of the research topic.")
    key_claims: List[str] = Field(..., description="The core arguments or hypotheses.")
    sources: List[str] = Field(..., description="The academic sources found.")

class FinalPaper(BaseModel):
    abstract: str = Field(..., description="A summary of the paper.")
    body_paragraphs: List[str] = Field(..., description="The main text.")
    conclusion: str = Field(..., description="The final conclusion.")
