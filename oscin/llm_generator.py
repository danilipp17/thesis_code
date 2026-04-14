"""
llm_generator.py
================
LLM-based ontology-to-source-code generation baseline.

Uses an LLM (via the Anthropic or OpenAI API) to generate source
code directly from the populated ontology instance.

Author: Dani Lippmann
Date: April 2026
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from oscin.llm_extractor import PROVIDERS, DEFAULT_MODELS

log = logging.getLogger("oscin")

PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "llm_generation.md"


def build_prompt(
    ontology_text: str,
    instance_data: str,
    target_framework: str,
) -> str:
    """
    Build the full prompt by filling in the template placeholders.
    """
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    prompt = template.replace("{{ontology}}", ontology_text)
    prompt = prompt.replace("{{instance_data}}", instance_data)
    prompt = prompt.replace("{{target_framework}}", target_framework)

    return prompt


def parse_generated_files(response_text: str, output_dir: Path) -> list[Path]:
    """Parse the LLM response into separate files."""
    # Match patterns like:
    # --- relative/path.py ---
    # ```python
    # <content>
    # ```
    pattern = r"---\s*(.*?)\s*---\s*\n```[a-zA-Z0-9_-]*\n(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)

    created_files = []
    for filepath_str, content in matches:
        # Sanitize path to prevent writing outside output_dir
        parts = Path(filepath_str.strip()).parts
        safe_parts = [
            p for p in parts if p not in ("..", "/", "\\") and not p.endswith(":")
        ]
        if not safe_parts:
            continue

        safe_path = output_dir.joinpath(*safe_parts)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content.strip() + "\n", encoding="utf-8")
        created_files.append(safe_path)

    # Fallback if the strict regex misses due to formatting variations
    if not created_files:
        log.warning(
            "  Could not extract file blocks with strict regex. Saving raw response to raw_output.txt"
        )
        raw_path = output_dir / "raw_output.txt"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(response_text, encoding="utf-8")
        created_files.append(raw_path)

    return created_files


def run_llm_generation(
    ttl_file: Path,
    output_dir: Path,
    target_framework: str,
    provider: str = "anthropic",
    model: str | None = None,
) -> list[Path]:
    """
    Run the full LLM-based generation pipeline.
    """
    # Resolve model
    if model is None:
        model = DEFAULT_MODELS.get(provider, "claude-sonnet-4-20250514")

    # Load ontology schema
    ontology_path = (
        Path(__file__).resolve().parent.parent / "ontology" / "agentoscin.ttl"
    )
    if not ontology_path.is_file():
        raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
    ontology_text = ontology_path.read_text(encoding="utf-8")

    # Load instance data
    if not ttl_file.is_file():
        raise FileNotFoundError(f"Instance TTL file not found: {ttl_file}")
    instance_data = ttl_file.read_text(encoding="utf-8")

    log.info(
        "  Loaded ontology schema (%d chars) and instance data (%d chars).",
        len(ontology_text),
        len(instance_data),
    )

    # Build prompt
    prompt = build_prompt(ontology_text, instance_data, target_framework)
    log.info("  Full prompt size: %d chars", len(prompt))

    # Call LLM
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS.keys())}"
        )

    call_fn = PROVIDERS[provider]
    response_text = call_fn(prompt, model=model)
    log.info("  Received response (%d chars)", len(response_text))

    # Parse response
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = parse_generated_files(response_text, output_dir)

    return created_files
