"""
generators
==========
Framework-specific code generators for the OSCIN reverse pipeline.

Each generator reads from the shared intermediate representations
(populated by :class:`oscin.reader.OntologyReader`) and produces
runnable source code for a specific agentic AI framework.
"""

from oscin.generators.base_generator import BaseCodeGenerator
from oscin.generators.crewai_generator import CrewAIGenerator
from oscin.generators.autogen_generator import AutoGenGenerator
from oscin.generators.langgraph_generator import LangGraphGenerator

__all__ = [
    "BaseCodeGenerator",
    "CrewAIGenerator",
    "AutoGenGenerator",
    "LangGraphGenerator",
]
