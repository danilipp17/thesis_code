"""
utils.py
========
Shared utility functions for the OSCIN pipeline.

These functions are used by both framework-specific parsers and the
shared ontology populator, so they live here to avoid cross-imports
between layers.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import json
from typing import Any


def pydantic_fields_to_json_schema(
    fields: dict[str, dict[str, str] | str],
) -> str:
    """
    Convert extracted Pydantic field definitions to a JSON Schema string.

    Accepts both legacy format ``{name: type_str}`` and enriched format
    ``{name: {"type": type_str, "description": desc}}``.

    Parameters
    ----------
    fields : dict
        Mapping of field names to type information.

    Returns
    -------
    str
        Compact JSON Schema string.
    """
    type_map = {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "Optional[str]": "string",
        "Optional[int]": "integer",
        "Optional[float]": "number",
        "Optional[bool]": "boolean",
    }

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    for name, field_info in fields.items():
        # Handle both dict and plain string formats
        if isinstance(field_info, dict):
            type_str = field_info.get("type", "str")
            desc = field_info.get("description", "")
        else:
            type_str = field_info
            desc = ""

        json_type = type_map.get(type_str, "string")
        prop: dict[str, Any] = {"type": json_type}
        if desc:
            prop["description"] = desc
        if type_str.startswith("Optional"):
            prop["nullable"] = True
        else:
            required.append(name)
        properties[name] = prop

    schema = {
        "type": "object",
        "properties": properties,
        "required": required,
    }
    return json.dumps(schema, separators=(",", ":"))


def safe_id(name: str) -> str:
    """
    Convert a name to a URI-safe identifier.

    Replaces spaces, hyphens, and dots with underscores.
    """
    return name.replace(" ", "_").replace("-", "_").replace(".", "_")
