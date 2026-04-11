"""
base_generator.py
=================
Abstract base class for all framework-specific code generators.

Generators consume intermediate representations (populated by an
:class:`oscin.reader.OntologyReader`) and produce framework source
code files in a target directory.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oscin.reader import OntologyReader

log = logging.getLogger("oscin")


class BaseCodeGenerator(ABC):
    """
    Abstract base class for framework-specific code generators.

    Parameters
    ----------
    reader : OntologyReader
        A reader whose ``read_all()`` has already been called.
    output_dir : Path
        Directory where the generated source files will be written.
    """

    def __init__(self, reader: OntologyReader, output_dir: Path):
        self.reader = reader
        self.output_dir = output_dir
        self._created_files: list[Path] = []

    @staticmethod
    @abstractmethod
    def framework_name() -> str:
        """Return the human-readable name of the target framework."""
        ...

    @abstractmethod
    def generate(self) -> list[Path]:
        """
        Generate all source files for the target framework.

        Returns
        -------
        list[Path]
            Paths to all files that were created.
        """
        ...

    # -----------------------------------------------------------
    # Shared helpers
    # -----------------------------------------------------------

    def _write_file(self, rel_path: str, content: str) -> Path:
        """
        Write a file relative to ``self.output_dir``.

        Creates parent directories as needed.  Returns the absolute
        path of the written file.
        """
        out = self.output_dir / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        self._created_files.append(out)
        log.info("  [WRITE] %s", out)
        return out

    @staticmethod
    def _to_snake(name: str) -> str:
        """Convert a string to snake_case."""
        import re
        # Insert underscore before uppercase letters
        s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
        return s.lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _to_class_name(name: str) -> str:
        """Convert a snake_case or space-separated name to PascalCase.

        If the name already contains mixed case (e.g. 'SerperDevTool'),
        it is returned as-is to avoid mangling.
        """
        import re
        # If name has no separators and already contains uppercase letters
        # beyond the first character, it's likely already PascalCase
        if "_" not in name and "-" not in name and " " not in name:
            if any(c.isupper() for c in name[1:]):
                return name
            # Single lowercase word — capitalize it
            return name[0].upper() + name[1:] if name else name
        return "".join(
            word.capitalize()
            for word in name.replace("-", "_").replace(" ", "_").split("_")
        )
