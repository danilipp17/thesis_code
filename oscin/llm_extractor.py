"""
llm_extractor.py
================
LLM-based ontology extraction baseline.

Uses an LLM (via the Anthropic or OpenAI API) to extract ontology
individuals directly from source code, as a comparison baseline to
the AST-based extraction pipeline.

The approach follows the methodology from AgentO (Siala et al.):
send the ontology schema + source code to an LLM and ask it to
produce populated Turtle output.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Load .env from common locations
load_dotenv()  # cwd
load_dotenv(Path.home() / ".env")  # home dir

log = logging.getLogger("oscin")

# Supported file extensions for source code collection
SOURCE_EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".txt", ".md"}

# Prompt template location
PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "llm_extraction.md"


def collect_source_files(source_dir: Path) -> str:
    """
    Collect all relevant source files from a directory into a single
    string, with file path headers.
    """
    parts: list[str] = []

    for filepath in sorted(source_dir.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix not in SOURCE_EXTENSIONS:
            continue
        if filepath.name.startswith("__"):
            continue
        if ".venv" in filepath.parts or "node_modules" in filepath.parts:
            continue

        rel_path = filepath.relative_to(source_dir)
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        parts.append(f"--- {rel_path} ---\n{content}")

    return "\n\n".join(parts)


def build_prompt(
    ontology_text: str,
    source_code: str,
    instance_namespace: str,
) -> str:
    """
    Build the full prompt by filling in the template placeholders.
    """
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    prompt = template.replace("{{ontology}}", ontology_text)
    prompt = prompt.replace("{{source_code}}", source_code)
    prompt = prompt.replace("{{instance_namespace}}", instance_namespace)

    return prompt


def extract_ttl_from_response(response_text: str) -> str:
    """
    Extract Turtle content from an LLM response.

    Handles responses wrapped in ```turtle ... ``` code blocks
    or returned as plain TTL text.
    """
    # Try to extract from code block
    match = re.search(
        r"```(?:turtle|ttl|n3|rdf)?\s*\n(.*?)```",
        response_text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()

    # If the response starts with @ or # (TTL prefixes/comments), use as-is
    stripped = response_text.strip()
    if stripped.startswith("@") or stripped.startswith("#"):
        return stripped

    return stripped


def call_anthropic(prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Call the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required for LLM extraction.\n"
            "Install it with: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    log.info("  Calling Anthropic API (model: %s)...", model)
    response = client.messages.create(
        model=model,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def call_openai(prompt: str, model: str = "gpt-4o") -> str:
    """Call the OpenAI API."""
    try:
        import openai
    except ImportError:
        raise ImportError(
            "The 'openai' package is required for LLM extraction with OpenAI.\n"
            "Install it with: pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = openai.OpenAI(api_key=api_key)

    log.info("  Calling OpenAI API (model: %s)...", model)
    response = client.chat.completions.create(
        model=model,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content


# Provider registry
PROVIDERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
}

# Default model per provider
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


def run_llm_extraction(
    source_dir: Path,
    output_path: Path,
    instance_namespace: str = "http://example.org/instance#",
    provider: str = "anthropic",
    model: str | None = None,
) -> Path:
    """
    Run the full LLM-based extraction pipeline.

    1. Load the ontology schema
    2. Collect source files
    3. Build the prompt
    4. Call the LLM
    5. Extract and validate TTL
    6. Write to output file

    Returns the output path.
    """
    # Resolve model
    if model is None:
        model = DEFAULT_MODELS.get(provider, "claude-sonnet-4-20250514")

    # Load ontology
    ontology_path = Path(__file__).resolve().parent.parent / "ontology" / "agentoscin.ttl"
    if not ontology_path.is_file():
        raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
    ontology_text = ontology_path.read_text(encoding="utf-8")
    log.info("  Loaded ontology from %s (%d chars)", ontology_path, len(ontology_text))

    # Collect source
    source_code = collect_source_files(source_dir)
    log.info("  Collected source code (%d chars) from %s", len(source_code), source_dir)

    # Build prompt
    prompt = build_prompt(ontology_text, source_code, instance_namespace)
    log.info("  Full prompt size: %d chars", len(prompt))

    # Call LLM
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS.keys())}")

    call_fn = PROVIDERS[provider]
    response_text = call_fn(prompt, model=model)
    log.info("  Received response (%d chars)", len(response_text))

    # Extract TTL
    ttl_content = extract_ttl_from_response(response_text)

    # Validate by parsing with rdflib
    from rdflib import Graph
    g = Graph()
    try:
        g.parse(data=ttl_content, format="turtle")
        log.info("  Parsed successfully: %d triples", len(g))
    except Exception as e:
        log.warning("  TTL parse warning: %s", e)
        log.warning("  Writing raw output anyway — may need manual fixes")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ttl_content, encoding="utf-8")
    log.info("  Written to: %s", output_path)

    return output_path
