"""
cli.py
======
Command-line entry point for the OSCIN extraction and generation pipeline.

Subcommands
-----------
``extract``
    Parse framework source code and produce a ``.ttl`` ontology instance.

``generate``
    Read a ``.ttl`` ontology instance and produce framework source code.

Usage examples::

    # Extract CrewAI source → TTL
    python -m oscin.cli extract examples/crewai/email-flow/source_files \\
        --framework crewai \\
        --system-name EmailFlowSystem \\
        --namespace "http://example.org/email_flow#" \\
        --output output/crewai/email_flow_ontology.ttl

    # Generate CrewAI code from TTL
    python -m oscin.cli generate output/crewai/email_flow_ontology.ttl \\
        --target-framework crewai \\
        --output-dir generated/crewai/email_flow/

    # Cross-framework: CrewAI TTL → AutoGen source code
    python -m oscin.cli generate output/crewai/self_eval_ontology.ttl \\
        --target-framework autogen \\
        --output-dir generated/autogen/self_eval/

    # LLM-based extraction baseline (requires ANTHROPIC_API_KEY)
    python -m oscin.cli extract-llm examples/crewai/email-flow/source_files \\
        --namespace "http://example.org/email_flow#" \\
        --output output/llm_baseline/email_flow_ontology.ttl \\
        --provider anthropic --model claude-sonnet-4-20250514

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from oscin.parsers import AutoGenParser, CrewAIParser, LangGraphParser
from oscin.populator import OntologyPopulator, print_validation_report
from oscin.reader import OntologyReader
from oscin.generators import AutoGenGenerator, CrewAIGenerator, LangGraphGenerator

# ---------------------------------------------------------------------------
# Registry maps
# ---------------------------------------------------------------------------
PARSERS = {
    "crewai": CrewAIParser,
    "autogen": AutoGenParser,
    "langgraph": LangGraphParser,
}

GENERATORS = {
    "crewai": CrewAIGenerator,
    "autogen": AutoGenGenerator,
    "langgraph": LangGraphGenerator,
}

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(message)s",
)


def main(argv: list[str] | None = None) -> None:
    """
    Parse arguments and dispatch to the correct subcommand.
    """
    ap = argparse.ArgumentParser(
        prog="oscin",
        description=(
            "OSCIN — Ontology-driven Source Code Interoperability.\n\n"
            "Extract agentic AI constructs from source code to an OWL\n"
            "ontology, or generate framework source code from an ontology."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = ap.add_subparsers(dest="command", help="Available commands")

    # ---------------------------------------------------------------
    # Subcommand: extract
    # ---------------------------------------------------------------
    extract_p = subparsers.add_parser(
        "extract",
        help="Extract source code → ontology TTL",
        description="Parse framework source code and produce a .ttl ontology instance.",
    )
    extract_p.add_argument(
        "source_dir",
        type=Path,
        help="Path to the source files directory to extract from.",
    )
    extract_p.add_argument(
        "--framework", "-f",
        choices=PARSERS.keys(),
        required=True,
        help="The agentic AI framework used in the source code.",
    )
    extract_p.add_argument(
        "--system-name", "-s",
        required=True,
        help="Human-readable name for the AgenticSystem individual.",
    )
    extract_p.add_argument(
        "--namespace", "-n",
        default="http://example.org/instance#",
        help="Base URI for instance individuals.  Default: http://example.org/instance#",
    )
    extract_p.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output_ontology.ttl"),
        help="Output file path for the Turtle-serialized ontology.",
    )
    extract_p.add_argument(
        "--no-report",
        action="store_true",
        help="Suppress the validation report at the end.",
    )

    # ---------------------------------------------------------------
    # Subcommand: extract-llm
    # ---------------------------------------------------------------
    llm_p = subparsers.add_parser(
        "extract-llm",
        help="Extract source code → ontology TTL using an LLM (baseline)",
        description=(
            "LLM-based extraction baseline. Sends the ontology schema and\n"
            "source code to an LLM and asks it to produce populated Turtle."
        ),
    )
    llm_p.add_argument(
        "source_dir",
        type=Path,
        help="Path to the source files directory to extract from.",
    )
    llm_p.add_argument(
        "--namespace", "-n",
        default="http://example.org/instance#",
        help="Base URI for instance individuals.  Default: http://example.org/instance#",
    )
    llm_p.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output_llm_ontology.ttl"),
        help="Output file path for the Turtle-serialized ontology.",
    )
    llm_p.add_argument(
        "--provider", "-p",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider to use. Default: anthropic",
    )
    llm_p.add_argument(
        "--model", "-m",
        default=None,
        help="Model name override (e.g. 'claude-sonnet-4-20250514', 'gpt-4o').",
    )

    # ---------------------------------------------------------------
    # Subcommand: generate
    # ---------------------------------------------------------------
    gen_p = subparsers.add_parser(
        "generate",
        help="Generate framework source code ← ontology TTL",
        description="Read a .ttl ontology instance and produce framework source code.",
    )
    gen_p.add_argument(
        "ttl_file",
        type=Path,
        help="Path to the .ttl ontology instance file to read.",
    )
    gen_p.add_argument(
        "--target-framework", "-t",
        choices=GENERATORS.keys(),
        required=True,
        help="The target framework to generate source code for.",
    )
    gen_p.add_argument(
        "--output-dir", "-d",
        type=Path,
        default=Path("generated"),
        help="Output directory for the generated source files.",
    )

    # ---------------------------------------------------------------
    # Subcommand: evaluate
    # ---------------------------------------------------------------
    eval_p = subparsers.add_parser(
        "evaluate",
        help="Evaluate extraction quality (single or pairwise)",
        description=(
            "Compute evaluation metrics for ontology extractions.\n"
            "Pass one TTL file for intrinsic metrics, or two for\n"
            "pairwise comparison (reference vs candidate)."
        ),
    )
    eval_p.add_argument(
        "reference",
        type=Path,
        help="Reference (gold standard) TTL file.",
    )
    eval_p.add_argument(
        "candidate",
        type=Path,
        nargs="?",
        default=None,
        help="Candidate TTL file to compare against reference. "
             "If omitted, only intrinsic metrics for the reference are shown.",
    )
    eval_p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output metrics as JSON instead of human-readable text.",
    )

    args = ap.parse_args(argv)

    if args.command is None:
        ap.print_help()
        sys.exit(1)

    if args.command == "extract":
        _run_extract(args)
    elif args.command == "extract-llm":
        _run_extract_llm(args)
    elif args.command == "generate":
        _run_generate(args)
    elif args.command == "evaluate":
        _run_evaluate(args)


# -------------------------------------------------------------------
# Extract pipeline
# -------------------------------------------------------------------

def _run_extract(args: argparse.Namespace) -> None:
    """Execute the extract subcommand."""
    source_dir: Path = args.source_dir.resolve()
    if not source_dir.is_dir():
        print(f"ERROR: Source directory does not exist: {source_dir}", file=sys.stderr)
        sys.exit(1)

    # Layer 1 + 2: Parsing
    parser_cls = PARSERS[args.framework]
    parser = parser_cls(source_dir)
    parser.parse_all()

    # Layer 3: Ontology Population
    populator = OntologyPopulator(
        parser,
        system_name=args.system_name,
        instance_namespace=args.namespace,
    )
    graph = populator.populate()

    # Serialization
    output_path: Path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output_path), format="turtle")

    log = logging.getLogger("oscin")
    log.info("")
    log.info("Ontology written to: %s", output_path)
    log.info("Total triples: %d", len(graph))

    # Validation Summary
    if not args.no_report:
        print("\n" + "=" * 60)
        print("EXTRACTION VALIDATION REPORT")
        print("=" * 60)
        print_validation_report(graph, parser)


# -------------------------------------------------------------------
# LLM Extract pipeline (baseline)
# -------------------------------------------------------------------

def _run_extract_llm(args: argparse.Namespace) -> None:
    """Execute the extract-llm subcommand."""
    from oscin.llm_extractor import run_llm_extraction

    log = logging.getLogger("oscin")

    source_dir: Path = args.source_dir.resolve()
    if not source_dir.is_dir():
        print(f"ERROR: Source directory does not exist: {source_dir}", file=sys.stderr)
        sys.exit(1)

    log.info("")
    log.info("=" * 60)
    log.info("STARTING LLM-BASED EXTRACTION (BASELINE)")
    log.info("Source directory: %s", source_dir)
    log.info("Provider: %s", args.provider)
    log.info("Model: %s", args.model or "(default)")
    log.info("=" * 60)

    output_path = run_llm_extraction(
        source_dir=source_dir,
        output_path=args.output.resolve(),
        instance_namespace=args.namespace,
        provider=args.provider,
        model=args.model,
    )

    log.info("")
    log.info("=" * 60)
    log.info("LLM EXTRACTION COMPLETE")
    log.info("Output: %s", output_path)
    log.info("=" * 60)


# -------------------------------------------------------------------
# Generate pipeline
# -------------------------------------------------------------------

def _run_generate(args: argparse.Namespace) -> None:
    """Execute the generate subcommand."""
    ttl_path: Path = args.ttl_file.resolve()
    if not ttl_path.is_file():
        print(f"ERROR: TTL file does not exist: {ttl_path}", file=sys.stderr)
        sys.exit(1)

    output_dir: Path = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read the ontology
    reader = OntologyReader(ttl_path)
    reader.read_all()

    # Generate source code
    gen_cls = GENERATORS[args.target_framework]
    generator = gen_cls(reader, output_dir)
    created = generator.generate()

    log = logging.getLogger("oscin")
    log.info("")
    log.info("Generated %d files in: %s", len(created), output_dir)


# -------------------------------------------------------------------
# Evaluate pipeline
# -------------------------------------------------------------------

def _run_evaluate(args: argparse.Namespace) -> None:
    """Execute the evaluate subcommand."""
    from rdflib import Graph
    from oscin.evaluator import (
        compute_intrinsic,
        compute_pairwise,
        format_intrinsic_report,
        format_pairwise_report,
        format_json_report,
    )

    ref_path: Path = args.reference.resolve()
    if not ref_path.is_file():
        print(f"ERROR: Reference file does not exist: {ref_path}", file=sys.stderr)
        sys.exit(1)

    ref_graph = Graph()
    ref_graph.parse(str(ref_path), format="turtle")
    intrinsic_ref = compute_intrinsic(ref_graph)

    intrinsic_cand = None
    pairwise = None

    if args.candidate:
        cand_path: Path = args.candidate.resolve()
        if not cand_path.is_file():
            print(f"ERROR: Candidate file does not exist: {cand_path}", file=sys.stderr)
            sys.exit(1)

        cand_graph = Graph()
        cand_graph.parse(str(cand_path), format="turtle")
        intrinsic_cand = compute_intrinsic(cand_graph)
        pairwise = compute_pairwise(ref_graph, cand_graph)

    if args.json_output:
        print(format_json_report(intrinsic_ref, intrinsic_cand, pairwise))
    else:
        print(format_intrinsic_report(intrinsic_ref, label=f"Reference ({ref_path.name})"))
        if intrinsic_cand and args.candidate:
            print()
            print(format_intrinsic_report(intrinsic_cand, label=f"Candidate ({args.candidate.name})"))
        if pairwise:
            print()
            print(format_pairwise_report(pairwise))


if __name__ == "__main__":
    main()
