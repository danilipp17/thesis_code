"""
run_crewai_roundtrip.py
=======================
Generic extract → generate round-trip driver for any OSCIN example.

Usage
-----
    # CrewAI example
    python run_crewai_roundtrip.py --framework crewai --example email-flow

    # LangGraph example (source file at examples/langgraph/ReAct/ReAct.py)
    python run_crewai_roundtrip.py --framework langgraph --example ReAct

    # Explicit paths (overrides defaults)
    python run_crewai_roundtrip.py \
        --framework crewai --example tech-blog \
        --source-dir examples/crewai/tech-blog/source_files \
        --ttl-out output/crewai/tech-blog.ttl \
        --gen-dir generated/crewai/tech-blog

Resolution rules (when --source-dir is omitted):
    1. ``examples/<framework>/<example>/source_files/``  (preferred)
    2. ``examples/<framework>/<example>/``                 (fallback, for flat examples)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from oscin.cli import main as oscin_main

PROJECT_ROOT = Path(__file__).resolve().parent


def resolve_source_dir(framework: str, example: str) -> Path:
    """Find the source directory for an example, preferring source_files/ subdir."""
    base = PROJECT_ROOT / "examples" / framework / example
    preferred = base / "source_files"
    if preferred.is_dir() and any(preferred.iterdir()):
        return preferred
    if base.is_dir() and any(base.iterdir()):
        return base
    raise FileNotFoundError(
        f"No source files found for {framework}/{example}. "
        f"Looked in {preferred} and {base}."
    )


def run_cli(argv: list[str]) -> int:
    """Invoke oscin.cli.main with the given argv; return the exit code (0 on success)."""
    try:
        oscin_main(argv)
        return 0
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0


def roundtrip(
    framework: str,
    example: str,
    source_dir: Path | None = None,
    ttl_out: Path | None = None,
    gen_dir: Path | None = None,
    system_name: str | None = None,
    namespace: str | None = None,
) -> tuple[Path, Path]:
    """Run extract + generate; return (ttl_path, generated_dir)."""
    source_dir = (source_dir or resolve_source_dir(framework, example)).resolve()
    ttl_out = (
        ttl_out or PROJECT_ROOT / "output" / framework / f"{example}.ttl"
    ).resolve()
    gen_dir = (
        gen_dir or PROJECT_ROOT / "generated" / framework / example
    ).resolve()
    system_name = system_name or example
    namespace = namespace or f"http://example.org/{example.replace('-', '_')}#"

    ttl_out.parent.mkdir(parents=True, exist_ok=True)
    gen_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print(f"ROUND-TRIP: {framework}/{example}")
    print(f"  source: {source_dir}")
    print(f"  ttl:    {ttl_out}")
    print(f"  gen:    {gen_dir}")
    print("=" * 72)

    print("\n--- EXTRACTION ---")
    code = run_cli([
        "extract",
        "--framework", framework,
        "--system-name", system_name,
        "--namespace", namespace,
        "--output", str(ttl_out),
        str(source_dir),
    ])
    if code != 0:
        raise SystemExit(f"Extraction failed (exit code {code})")

    print("\n--- GENERATION ---")
    code = run_cli([
        "generate",
        "--target-framework", framework,
        "--output-dir", str(gen_dir),
        str(ttl_out),
    ])
    if code != 0:
        raise SystemExit(f"Generation failed (exit code {code})")

    print("\n--- DONE ---")
    print(f"TTL: {ttl_out}")
    print(f"Generated: {gen_dir}")
    return ttl_out, gen_dir


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Extract → generate round-trip for any OSCIN example."
    )
    ap.add_argument(
        "--framework", "-f",
        choices=["crewai", "langgraph", "autogen"],
        default="crewai",
        help="Source framework (default: crewai).",
    )
    ap.add_argument(
        "--example", "-e",
        default="email-flow",
        help="Example name under examples/<framework>/ (default: email-flow).",
    )
    ap.add_argument(
        "--source-dir", type=Path, default=None,
        help="Explicit source directory (overrides resolution).",
    )
    ap.add_argument(
        "--ttl-out", type=Path, default=None,
        help="Explicit TTL output path.",
    )
    ap.add_argument(
        "--gen-dir", type=Path, default=None,
        help="Explicit generation output directory.",
    )
    ap.add_argument(
        "--system-name", default=None,
        help="AgenticSystem name (defaults to example name).",
    )
    ap.add_argument(
        "--namespace", default=None,
        help="Instance namespace URI.",
    )
    args = ap.parse_args(argv)

    roundtrip(
        framework=args.framework,
        example=args.example,
        source_dir=args.source_dir,
        ttl_out=args.ttl_out,
        gen_dir=args.gen_dir,
        system_name=args.system_name,
        namespace=args.namespace,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
