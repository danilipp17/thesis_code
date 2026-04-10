"""
oscin.parsers
=============
Framework-specific source code parsers.

Each parser inherits from :class:`oscin.base_parser.BaseSourceParser`
and populates the shared intermediate representation defined in
:mod:`oscin.intermediate`.
"""

from oscin.parsers.crewai_parser import CrewAIParser
from oscin.parsers.autogen_parser import AutoGenParser
from oscin.parsers.langgraph_parser import LangGraphParser

__all__ = ["CrewAIParser", "AutoGenParser", "LangGraphParser"]
