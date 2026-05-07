"""
llm_fixup.py
===========
LLM-based fixup of deterministically generated source code.

Takes the skeleton code produced by the template-based generator and an
ontology TTL file, sends both to an LLM with a targeted prompt listing
known generation issues, and writes the fixed-up code to an output directory.

Pipeline:
    skeleton code (from deterministic generator)
        + ontology TTL (from AST extraction)
            → LLM prompt
                → fixed source code (runnable)

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    May 2026
"""

from __future__ import annotations

import logging
from pathlib import Path

from oscin.llm_extractor import PROVIDERS, DEFAULT_MODELS
from oscin.llm_generator import parse_generated_files

log = logging.getLogger("oscin")

PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "llm_fixup.md"


def collect_skeleton_files(generated_dir: Path) -> str:
    """Collect all .py files from the skeleton directory into a single
    string with --- filepath --- headers, matching the LLM output format."""
    parts: list[str] = []
    for filepath in sorted(generated_dir.rglob("*.py")):
        if "__pycache__" in filepath.parts:
            continue
        rel_path = filepath.relative_to(generated_dir)
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        parts.append(f"--- {rel_path} ---\n```python\n{content}\n```")
    return "\n\n".join(parts)


def build_fixup_prompt(
    instance_data: str,
    skeleton_code: str,
    target_framework: str,
) -> str:
    """Build the full prompt by filling in the template placeholders."""
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    prompt = template.replace("{{instance_data}}", instance_data)
    prompt = prompt.replace("{{skeleton_code}}", skeleton_code)
    prompt = prompt.replace("{{target_framework}}", target_framework)

    return prompt


def run_llm_fixup(
    generated_dir: Path,
    ttl_file: Path,
    target_framework: str,
    output_dir: Path | None = None,
    provider: str = "openai",
    model: str | None = None,
) -> Path:
    """
    Run the LLM fixup pipeline.

    Parameters
    ----------
    generated_dir : Path
        Directory containing the skeleton code (from deterministic generator).
    ttl_file : Path
        Path to the populated TTL file (from AST extraction).
    target_framework : str
        Target framework name (crewai, langgraph, autogen).
    output_dir : Path | None
        Directory to write fixed-up code. Defaults to generated_dir + "_fixed".
    provider : str
        LLM provider: "openai" or "anthropic".
    model : str | None
        Model name. Defaults to provider's default.

    Returns
    -------
    Path
        Path to the output directory with fixed-up files.
    """
    if model is None:
        model = DEFAULT_MODELS.get(provider, "gpt-4o")

    generated_dir = Path(generated_dir).resolve()
    ttl_file = Path(ttl_file).resolve()

    if not generated_dir.is_dir():
        raise FileNotFoundError(f"Skeleton directory not found: {generated_dir}")
    if not ttl_file.is_file():
        raise FileNotFoundError(f"TTL file not found: {ttl_file}")

    if output_dir is None:
        output_dir = generated_dir.parent / (generated_dir.name + "_fixed")
    output_dir = Path(output_dir).resolve()

    # Collect skeleton code
    skeleton_code = collect_skeleton_files(generated_dir)
    if not skeleton_code.strip():
        raise ValueError(f"No .py files found in {generated_dir}")
    log.info("  Collected skeleton code (%d chars)", len(skeleton_code))

    # Load TTL instance data
    instance_data = ttl_file.read_text(encoding="utf-8")
    log.info("  Loaded instance data (%d chars)", len(instance_data))

    # Build prompt
    prompt = build_fixup_prompt(instance_data, skeleton_code, target_framework)
    log.info("  Full prompt size: %d chars", len(prompt))

    # Call LLM
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS.keys())}"
        )
    call_fn = PROVIDERS[provider]
    response_text = call_fn(prompt, model=model)
    log.info("  Received response (%d chars)", len(response_text))

    # Parse response into files
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = parse_generated_files(response_text, output_dir)

    if not created_files:
        log.warning("  No files extracted from LLM response. Saving raw output.")
        raw_path = output_dir / "raw_output.txt"
        raw_path.write_text(response_text, encoding="utf-8")

    log.info("  Wrote %d files to %s", len(created_files), output_dir)
    return output_dir