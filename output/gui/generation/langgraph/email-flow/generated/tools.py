"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool

@tool
def serper_dev_tool(**kwargs) -> str:
    """SerperDevTool
    
    """
    raise NotImplementedError("TODO: implement SerperDevTool")

@tool
def create_draft(**kwargs) -> str:
    """Create Draft
    Useful to create an email draft.
The input to this tool should be a pipe (|) separated text
of length 3 (three), representing who to send the email to,
the subject of the email and the actual message.
For example, `lorem@ipsum.com|Nice To Meet You|Hey it was great to meet you.`.
    """
    raise NotImplementedError("TODO: implement Create Draft")

@tool
def gmail_get_thread(**kwargs) -> str:
    """GmailGetThread
    
    """
    raise NotImplementedError("TODO: implement GmailGetThread")

@tool
def tavily_search_results(**kwargs) -> str:
    """TavilySearchResults
    
    """
    raise NotImplementedError("TODO: implement TavilySearchResults")

