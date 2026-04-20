"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool

@tool
def save(filename: str) -> str:
    """save
    Save the current document to a text file and finish the process.

Args:
    filename: Name for the text file.
    """
    raise NotImplementedError("TODO: implement save")

@tool
def update(content: str) -> str:
    """update
    Updates the document with the provided content.
    """
    raise NotImplementedError("TODO: implement update")

