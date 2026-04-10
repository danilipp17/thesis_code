"""
base_parser.py
==============
Abstract base class that every framework-specific parser must implement.

The base parser defines the shared **output contract**: a set of
dictionaries holding intermediate representations.  Subclasses fill
these dictionaries by implementing :meth:`parse_all`.

The :class:`OntologyPopulator` accepts any ``BaseSourceParser``
instance, so it works with every framework without modification.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from oscin.intermediate import (
    ExtractedAgent,
    ExtractedFlow,
    ExtractedPydanticModel,
    ExtractedTask,
    ExtractedTeam,
    ExtractedTool,
)

log = logging.getLogger("oscin")


class BaseSourceParser(ABC):
    """
    Abstract base for framework-specific source code parsers.

    Every concrete parser must:

    1. Accept a ``source_dir`` pointing to the project's source files.
    2. Implement :meth:`parse_all` to fill the intermediate-representation
       dictionaries defined below.
    3. Implement :meth:`framework_name` to return a human-readable label
       (used in the ontology's ``hasSourceFramework`` property).

    The dictionaries use string keys (agent names, task names, etc.)
    that are locally unique within a single extraction run.
    """

    def __init__(self, source_dir: Path):
        self.source_dir = source_dir

        # Intermediate-representation stores — populated by parse_all()
        self.agents: dict[str, ExtractedAgent] = {}
        self.tasks: dict[str, ExtractedTask] = {}
        self.tools: dict[str, ExtractedTool] = {}
        self.teams: dict[str, ExtractedTeam] = {}
        self.flow: Optional[ExtractedFlow] = None
        self.pydantic_models: dict[str, ExtractedPydanticModel] = {}

    # -----------------------------------------------------------
    # Abstract interface
    # -----------------------------------------------------------

    @abstractmethod
    def parse_all(self) -> None:
        """
        Execute the full extraction pipeline.

        Implementations should populate ``self.agents``, ``self.tasks``,
        ``self.tools``, ``self.teams``, ``self.flow``, and
        ``self.pydantic_models`` as applicable.
        """
        ...

    @staticmethod
    @abstractmethod
    def framework_name() -> str:
        """
        Return the canonical framework name.

        This value is stored as ``agento:hasSourceFramework`` on the
        ``AgenticSystem`` individual in the output ontology.

        Examples: ``"CrewAI"``, ``"AutoGen"``, ``"LangGraph"``
        """
        ...

    # -----------------------------------------------------------
    # Shared utilities available to all parsers
    # -----------------------------------------------------------

    def log_extraction_summary(self) -> None:
        """Log a summary of everything that was extracted."""
        log.info("=" * 60)
        log.info("EXTRACTION SUMMARY")
        log.info("  Framework: %s", self.framework_name())
        log.info("  Agents: %d", len(self.agents))
        log.info("  Tasks:  %d", len(self.tasks))
        log.info("  Tools:  %d", len(self.tools))
        log.info("  Teams:  %d", len(self.teams))
        log.info("  Flow:   %s", "yes" if self.flow else "no")
        log.info("  Pydantic models: %d", len(self.pydantic_models))
        log.info("=" * 60)
