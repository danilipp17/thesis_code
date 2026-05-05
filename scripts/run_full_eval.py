"""
run_full_eval.py
================
Comprehensive evaluation script for the thesis.

Runs:
1. AST same-framework roundtrip for all examples
2. AST cross-framework roundtrip (CrewAI↔LangGraph)
3. LLM extraction for all examples (N=1, OpenAI gpt-4o)
4. LLM same-framework roundtrip for all examples
5. LLM cross-framework roundtrip (CrewAI↔LangGraph)

Output: output/eval_full/
"""
from __future__ import annotations

import json
import logging
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rdflib import Graph

from evaluation.pipelines.roundtrip import run_roundtrip
from oscin.llm_extractor import run_llm_extraction
from oscin.llm_generator import run_llm_generation
from oscin.evaluator import compute_pairwise, compute_intrinsic
from evaluation.metrics import ast_diff, ttl_pairwise, ttl_fuzzy_match

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
log = logging.getLogger("eval_full")

OUT_ROOT = ROOT / "output" / "eval_full"

# All examples
CREWAI_EXAMPLES = [
    "academic-research-flow",
    "code-review",
    "comprehensive",
    "content-pipeline",
    "email-flow",
    "self-eval-loop-flow",
    "tech-blog",
    "unseen-hiring-pipeline",
]

LANGGRAPH_EXAMPLES = [
    "ReAct",
    "drafter",
    "memoryagent",
    "plan-execute",
    "ragagent",
    "reflexion",
    "research-assistant",
    "tech-blog",
    "unseen-customer-support",
]

AUTOGEN_EXAMPLES = [
    "code-review",
    "company-research",
    "content-pipeline",
    "data-analysis-0.4",
    "literature-review",
    "tech-blog",
    "travel-planning",
    "unseen-debate",
]

ALL_EXAMPLES = (
    [("crewai", ex) for ex in CREWAI_EXAMPLES]
    + [("langgraph", ex) for ex in LANGGRAPH_EXAMPLES]
    + [("autogen", ex) for ex in AUTOGEN_EXAMPLES]
)

LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o"


def resolve_example_root(fw: str, name: str) -> Path:
    return ROOT / "examples" / fw / name


def safe_run(label: str, fn, *args, **kwargs):
    """Run a function, catch errors, return result or None."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log.error(f"  FAILED [{label}]: {e}")
        traceback.print_exc()
        return None


def load_graph(path: Path) -> Graph | None:
    if not path.exists():
        return None
    g = Graph()
    try:
        g.parse(str(path), format="turtle")
        return g
    except Exception as e:
        log.warning(f"  Parse failed for {path}: {e}")
        return None


# ===================================================================
# PHASE 1: AST Same-Framework Roundtrips
# ===================================================================

def run_ast_same_fw():
    """Run AST same-framework roundtrip for all examples."""
    log.info("=" * 60)
    log.info("PHASE 1: AST Same-Framework Roundtrips")
    log.info("=" * 60)

    out_dir = OUT_ROOT / "ast_same_fw"
    results = []

    for fw, ex in ALL_EXAMPLES:
        log.info(f"\n  [{fw}] {ex}")
        example_root = resolve_example_root(fw, ex)
        try:
            report = run_roundtrip(
                example_root, fw,
                skip_execution=True,
                out_root=out_dir,
            )
            results.append(report)
            # Print key metrics
            pw = report.get("metrics", {}).get("ttl_pairwise", {})
            ast = report.get("metrics", {}).get("ast_diff", {})
            triple_f1 = pw.get("triple_f1", "N/A")
            prop_f1 = pw.get("property_f1", "N/A")
            ind_f1 = pw.get("individual_f1", "N/A")
            ast_f1 = ast.get("overall", {}).get("f1", "N/A") if isinstance(ast, dict) else "N/A"
            log.info(f"    Triple F1={triple_f1}, Prop F1={prop_f1}, Ind F1={ind_f1}, AST F1={ast_f1}")
        except Exception as e:
            log.error(f"    FAILED: {e}")
            results.append({"example": ex, "framework": fw, "error": str(e)})

    # Save consolidated results
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "all_results.json").write_text(json.dumps(results, indent=2, default=str))
    log.info(f"\n  Saved {len(results)} results to {out_dir / 'all_results.json'}")
    return results


# ===================================================================
# PHASE 2: AST Cross-Framework Roundtrips
# ===================================================================

def run_ast_cross_fw():
    """Run AST cross-framework roundtrip: CrewAI↔LangGraph."""
    log.info("=" * 60)
    log.info("PHASE 2: AST Cross-Framework Roundtrips")
    log.info("=" * 60)

    out_dir = OUT_ROOT / "ast_cross_fw"
    results = []

    # CrewAI → LangGraph
    for ex in CREWAI_EXAMPLES:
        log.info(f"\n  [crewai→langgraph] {ex}")
        example_root = resolve_example_root("crewai", ex)
        try:
            report = run_roundtrip(
                example_root, "crewai",
                target_framework="langgraph",
                skip_execution=True,
                out_root=out_dir / "crewai_to_langgraph",
            )
            report["direction"] = "crewai→langgraph"
            results.append(report)
            pw = report.get("metrics", {}).get("ttl_pairwise", {})
            log.info(f"    Triple F1={pw.get('triple_f1', 'N/A')}, Aligned={pw.get('aligned_triple_f1', 'N/A')}")
        except Exception as e:
            log.error(f"    FAILED: {e}")
            results.append({"example": ex, "framework": "crewai", "target": "langgraph", "error": str(e)})

    # LangGraph → CrewAI
    for ex in LANGGRAPH_EXAMPLES:
        log.info(f"\n  [langgraph→crewai] {ex}")
        example_root = resolve_example_root("langgraph", ex)
        try:
            report = run_roundtrip(
                example_root, "langgraph",
                target_framework="crewai",
                skip_execution=True,
                out_root=out_dir / "langgraph_to_crewai",
            )
            report["direction"] = "langgraph→crewai"
            results.append(report)
            pw = report.get("metrics", {}).get("ttl_pairwise", {})
            log.info(f"    Triple F1={pw.get('triple_f1', 'N/A')}, Aligned={pw.get('aligned_triple_f1', 'N/A')}")
        except Exception as e:
            log.error(f"    FAILED: {e}")
            results.append({"example": ex, "framework": "langgraph", "target": "crewai", "error": str(e)})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "all_results.json").write_text(json.dumps(results, indent=2, default=str))
    log.info(f"\n  Saved {len(results)} results to {out_dir / 'all_results.json'}")
    return results


# ===================================================================
# PHASE 3: LLM Extraction (all examples)
# ===================================================================

def run_llm_extraction_all():
    """Run LLM extraction for all examples and compare to AST extraction."""
    log.info("=" * 60)
    log.info("PHASE 3: LLM Extraction (OpenAI gpt-4o)")
    log.info("=" * 60)

    out_dir = OUT_ROOT / "llm_extraction"
    results = []

    for fw, ex in ALL_EXAMPLES:
        log.info(f"\n  [{fw}] {ex}")
        example_root = resolve_example_root(fw, ex)

        # Resolve source dir
        source_dir = example_root / "source_files"
        if not source_dir.is_dir():
            source_dir = example_root
        if not source_dir.is_dir():
            log.warning(f"    Source dir not found, skipping")
            continue

        llm_ttl_path = out_dir / fw / ex / "extracted_llm.ttl"
        ast_ttl_path = out_dir / fw / ex / "extracted_ast.ttl"

        # Step 1: AST extraction (for comparison baseline)
        from evaluation.pipelines._common import run_oscin, default_namespace, default_system_name
        ns = default_namespace(ex)
        system_name = default_system_name(ex)

        if not ast_ttl_path.exists():
            try:
                run_oscin([
                    "extract", str(source_dir),
                    "--framework", fw,
                    "--system-name", system_name,
                    "--namespace", ns,
                    "--output", str(ast_ttl_path),
                    "--no-report",
                ])
            except Exception as e:
                log.error(f"    AST extraction failed: {e}")
                results.append({"framework": fw, "example": ex, "error": f"AST extract: {e}"})
                continue

        # Step 2: LLM extraction
        if not llm_ttl_path.exists():
            try:
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=llm_ttl_path,
                    instance_namespace=ns,
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM extraction failed: {e}")
                results.append({"framework": fw, "example": ex, "error": f"LLM extract: {e}"})
                continue

        # Step 3: Compare LLM vs AST
        g_ast = load_graph(ast_ttl_path)
        g_llm = load_graph(llm_ttl_path)

        if g_ast and g_llm:
            pw = compute_pairwise(g_ast, g_llm)
            intr_ast = compute_intrinsic(g_ast)
            intr_llm = compute_intrinsic(g_llm)
            result = {
                "framework": fw,
                "example": ex,
                "ast_triples": intr_ast.abox_triples,
                "ast_individuals": intr_ast.total_individuals,
                "llm_triples": intr_llm.abox_triples,
                "llm_individuals": intr_llm.total_individuals,
                "llm_vs_ast": {
                    "triple_f1": pw.triple_f1,
                    "property_f1": pw.property_f1,
                    "individual_f1": pw.individual_f1,
                    "aligned_triple_f1": pw.aligned_triple_f1,
                    "literal_overlap": pw.literal_overlap,
                    "missing_properties": pw.missing_properties,
                    "extra_properties": pw.extra_properties,
                    "missing_individuals": pw.missing_individuals,
                    "extra_individuals": pw.extra_individuals,
                },
            }
            log.info(f"    LLM vs AST: Triple F1={pw.triple_f1:.3f}, Prop F1={pw.property_f1:.3f}, Ind F1={pw.individual_f1:.3f}")
            results.append(result)
        else:
            results.append({"framework": fw, "example": ex, "error": "graph parse failed"})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "all_results.json").write_text(json.dumps(results, indent=2, default=str))
    log.info(f"\n  Saved {len(results)} results to {out_dir / 'all_results.json'}")
    return results


# ===================================================================
# PHASE 4: LLM Same-Framework Roundtrip
# ===================================================================

def run_llm_same_fw_roundtrip():
    """
    LLM same-framework roundtrip:
    source → LLM extract → TTL₁ → LLM generate(same_fw) → source′ → AST extract → TTL₂
    Compare TTL₁ vs TTL₂
    """
    log.info("=" * 60)
    log.info("PHASE 4: LLM Same-Framework Roundtrip")
    log.info("=" * 60)

    out_dir = OUT_ROOT / "llm_same_fw"
    results = []

    for fw, ex in ALL_EXAMPLES:
        log.info(f"\n  [{fw}] {ex}")
        example_root = resolve_example_root(fw, ex)
        work = out_dir / fw / ex
        work.mkdir(parents=True, exist_ok=True)

        source_dir = example_root / "source_files"
        if not source_dir.is_dir():
            source_dir = example_root

        ttl1_path = work / "ttl1_llm.ttl"
        gen_dir = work / "generated"
        ttl2_path = work / "ttl2.ttl"

        from evaluation.pipelines._common import default_namespace, default_system_name, run_oscin
        ns = default_namespace(ex)
        system_name = default_system_name(ex)

        # Step 1: LLM extraction → TTL₁
        if not ttl1_path.exists():
            try:
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=ttl1_path,
                    instance_namespace=ns,
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM extract failed: {e}")
                results.append({"framework": fw, "example": ex, "error": f"LLM extract: {e}"})
                continue

        # Step 2: LLM generation → source′
        if not gen_dir.exists() or not list(gen_dir.glob("*.py")):
            try:
                run_llm_generation(
                    ttl_file=ttl1_path,
                    output_dir=gen_dir,
                    target_framework=fw,
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM generate failed: {e}")
                results.append({"framework": fw, "example": ex, "error": f"LLM generate: {e}"})
                continue

        # Step 3: AST re-extraction → TTL₂
        if not ttl2_path.exists():
            try:
                run_oscin([
                    "extract", str(gen_dir),
                    "--framework", fw,
                    "--system-name", system_name,
                    "--namespace", ns,
                    "--output", str(ttl2_path),
                    "--no-report",
                ])
            except Exception as e:
                log.error(f"    AST re-extract failed: {e}")
                results.append({"framework": fw, "example": ex, "error": f"re-extract: {e}"})
                continue

        # Step 4: Compare TTL₁ vs TTL₂
        g1 = load_graph(ttl1_path)
        g2 = load_graph(ttl2_path)

        if g1 and g2:
            pw = compute_pairwise(g1, g2)
            result = {
                "framework": fw,
                "example": ex,
                "ttl1_triples": len(g1),
                "ttl2_triples": len(g2),
                "metrics": {
                    "triple_f1": pw.triple_f1,
                    "property_f1": pw.property_f1,
                    "individual_f1": pw.individual_f1,
                    "aligned_triple_f1": pw.aligned_triple_f1,
                    "literal_overlap": pw.literal_overlap,
                },
            }
            log.info(f"    Triple F1={pw.triple_f1:.3f}, Prop F1={pw.property_f1:.3f}, Ind F1={pw.individual_f1:.3f}")
            results.append(result)
        else:
            results.append({"framework": fw, "example": ex, "error": "graph parse failed"})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "all_results.json").write_text(json.dumps(results, indent=2, default=str))
    log.info(f"\n  Saved {len(results)} results")
    return results


# ===================================================================
# PHASE 5: LLM Cross-Framework Roundtrip
# ===================================================================

def run_llm_cross_fw_roundtrip():
    """
    LLM cross-framework roundtrip:
    source_A → LLM extract → TTL₁ → LLM generate(B) → source_B → AST extract(B) → TTL₂
    """
    log.info("=" * 60)
    log.info("PHASE 5: LLM Cross-Framework Roundtrip")
    log.info("=" * 60)

    out_dir = OUT_ROOT / "llm_cross_fw"
    results = []

    # CrewAI → LangGraph
    for ex in CREWAI_EXAMPLES:
        log.info(f"\n  [crewai→langgraph] {ex}")
        example_root = resolve_example_root("crewai", ex)
        work = out_dir / "crewai_to_langgraph" / ex
        work.mkdir(parents=True, exist_ok=True)

        source_dir = example_root / "source_files"
        if not source_dir.is_dir():
            source_dir = example_root

        ttl1_path = work / "ttl1_llm.ttl"
        gen_dir = work / "generated"
        ttl2_path = work / "ttl2.ttl"

        from evaluation.pipelines._common import default_namespace, default_system_name, run_oscin
        ns = default_namespace(ex)
        system_name = default_system_name(ex)

        # Step 1: LLM extraction
        if not ttl1_path.exists():
            try:
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=ttl1_path,
                    instance_namespace=ns,
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM extract failed: {e}")
                results.append({"example": ex, "direction": "crewai→langgraph", "error": str(e)})
                continue

        # Step 2: LLM generate to LangGraph
        if not gen_dir.exists() or not list(gen_dir.glob("*.py")):
            try:
                run_llm_generation(
                    ttl_file=ttl1_path,
                    output_dir=gen_dir,
                    target_framework="langgraph",
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM generate failed: {e}")
                results.append({"example": ex, "direction": "crewai→langgraph", "error": str(e)})
                continue

        # Step 3: AST re-extract as LangGraph
        if not ttl2_path.exists():
            try:
                run_oscin([
                    "extract", str(gen_dir),
                    "--framework", "langgraph",
                    "--system-name", system_name,
                    "--namespace", ns,
                    "--output", str(ttl2_path),
                    "--no-report",
                ])
            except Exception as e:
                log.error(f"    Re-extract failed: {e}")
                results.append({"example": ex, "direction": "crewai→langgraph", "error": str(e)})
                continue

        # Step 4: Compare
        g1 = load_graph(ttl1_path)
        g2 = load_graph(ttl2_path)
        if g1 and g2:
            pw = compute_pairwise(g1, g2)
            result = {
                "example": ex,
                "direction": "crewai→langgraph",
                "metrics": {
                    "triple_f1": pw.triple_f1,
                    "aligned_triple_f1": pw.aligned_triple_f1,
                    "property_f1": pw.property_f1,
                    "individual_f1": pw.individual_f1,
                    "literal_overlap": pw.literal_overlap,
                },
            }
            log.info(f"    Triple F1={pw.triple_f1:.3f}, Aligned={pw.aligned_triple_f1:.3f}")
            results.append(result)
        else:
            results.append({"example": ex, "direction": "crewai→langgraph", "error": "graph parse failed"})

    # LangGraph → CrewAI
    for ex in LANGGRAPH_EXAMPLES:
        log.info(f"\n  [langgraph→crewai] {ex}")
        example_root = resolve_example_root("langgraph", ex)
        work = out_dir / "langgraph_to_crewai" / ex
        work.mkdir(parents=True, exist_ok=True)

        source_dir = example_root / "source_files"
        if not source_dir.is_dir():
            source_dir = example_root

        ttl1_path = work / "ttl1_llm.ttl"
        gen_dir = work / "generated"
        ttl2_path = work / "ttl2.ttl"

        ns = default_namespace(ex)
        system_name = default_system_name(ex)

        # Step 1: LLM extraction
        if not ttl1_path.exists():
            try:
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=ttl1_path,
                    instance_namespace=ns,
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM extract failed: {e}")
                results.append({"example": ex, "direction": "langgraph→crewai", "error": str(e)})
                continue

        # Step 2: LLM generate to CrewAI
        if not gen_dir.exists() or not list(gen_dir.glob("**/*.py")):
            try:
                run_llm_generation(
                    ttl_file=ttl1_path,
                    output_dir=gen_dir,
                    target_framework="crewai",
                    provider=LLM_PROVIDER,
                    model=LLM_MODEL,
                )
            except Exception as e:
                log.error(f"    LLM generate failed: {e}")
                results.append({"example": ex, "direction": "langgraph→crewai", "error": str(e)})
                continue

        # Step 3: AST re-extract as CrewAI
        if not ttl2_path.exists():
            try:
                run_oscin([
                    "extract", str(gen_dir),
                    "--framework", "crewai",
                    "--system-name", system_name,
                    "--namespace", ns,
                    "--output", str(ttl2_path),
                    "--no-report",
                ])
            except Exception as e:
                log.error(f"    Re-extract failed: {e}")
                results.append({"example": ex, "direction": "langgraph→crewai", "error": str(e)})
                continue

        # Step 4: Compare
        g1 = load_graph(ttl1_path)
        g2 = load_graph(ttl2_path)
        if g1 and g2:
            pw = compute_pairwise(g1, g2)
            result = {
                "example": ex,
                "direction": "langgraph→crewai",
                "metrics": {
                    "triple_f1": pw.triple_f1,
                    "aligned_triple_f1": pw.aligned_triple_f1,
                    "property_f1": pw.property_f1,
                    "individual_f1": pw.individual_f1,
                    "literal_overlap": pw.literal_overlap,
                },
            }
            log.info(f"    Triple F1={pw.triple_f1:.3f}, Aligned={pw.aligned_triple_f1:.3f}")
            results.append(result)
        else:
            results.append({"example": ex, "direction": "langgraph→crewai", "error": "graph parse failed"})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "all_results.json").write_text(json.dumps(results, indent=2, default=str))
    log.info(f"\n  Saved {len(results)} results")
    return results


# ===================================================================
# MAIN
# ===================================================================

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, nargs="*", default=[1, 2, 3, 4, 5],
                    help="Which phases to run (1-5). Default: all")
    args = ap.parse_args()

    phases = args.phase

    if 1 in phases:
        run_ast_same_fw()
    if 2 in phases:
        run_ast_cross_fw()
    if 3 in phases:
        run_llm_extraction_all()
    if 4 in phases:
        run_llm_same_fw_roundtrip()
    if 5 in phases:
        run_llm_cross_fw_roundtrip()

    log.info("\n\nDONE. All results in: %s", OUT_ROOT)


if __name__ == "__main__":
    main()
