"""
Run LLM extraction baseline (N=3) on a representative subset and compute
pairwise metrics vs the deterministic AST baseline plus within-LLM
reproducibility.

Output:
    output/llm_baseline/run<idx>/<framework>/<example>/extracted.ttl
    output/llm_baseline/summary.json
    output/llm_baseline/summary.md
"""
from __future__ import annotations

import json
import re
import sys
from itertools import combinations
from pathlib import Path
from statistics import mean, pstdev

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oscin.llm_extractor import run_llm_extraction
from oscin.evaluator import compute_pairwise, compute_intrinsic

EXAMPLES = [
    ("crewai", "email-flow", ROOT / "examples/crewai/email-flow/source_files"),
    ("langgraph", "ReAct", ROOT / "examples/langgraph/ReAct"),
    ("autogen", "code-review", ROOT / "examples/autogen/code-review/source_files"),
]
N_RUNS = 3
PROVIDER = "openai"
MODEL = "gpt-4o"
OUT_ROOT = ROOT / "output/llm_baseline"


def _repair_ttl(text: str) -> str:
    # Common LLM mistake: end-of-statement ';' followed by blank line and a new subject.
    # Replace ';\n\n<NewSubject>' with '.\n\n<NewSubject>'.
    text = re.sub(r";\s*\n\s*\n(?=[:a-zA-Z_])", ".\n\n", text)
    # Same pattern when followed by '### ' markdown header (TTL comment line).
    text = re.sub(r";\s*\n\s*\n###", ".\n\n###", text)
    return text


def load_graph(p: Path) -> Graph | None:
    g = Graph()
    try:
        g.parse(str(p), format="turtle")
        return g
    except Exception:
        # Attempt heuristic repair
        try:
            text = Path(p).read_text(encoding="utf-8")
            repaired = _repair_ttl(text)
            g2 = Graph()
            g2.parse(data=repaired, format="turtle")
            print(f"  parse OK after repair for {p}")
            return g2
        except Exception as e:
            print(f"  parse failed for {p}: {str(e)[:160]}")
            return None


def pair_metrics(ref: Graph, cand: Graph) -> dict:
    m = compute_pairwise(ref, cand)
    return {
        "individual_f1": m.individual_f1,
        "property_f1": m.property_f1,
        "triple_f1": m.triple_f1,
        "literal_overlap": m.literal_overlap,
    }


def intrinsic(g: Graph) -> dict:
    m = compute_intrinsic(g)
    return {
        "intrinsic_triples": m.abox_triples,
        "intrinsic_individuals": m.total_individuals,
        "intrinsic_properties": m.property_count,
        "intrinsic_density": m.information_density,
    }


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: dict = {"provider": PROVIDER, "model": MODEL, "n_runs": N_RUNS, "examples": []}

    for fw, ex, src in EXAMPLES:
        print(f"\n=== {fw}/{ex} ===")
        ast_ttl = ROOT / f"output/extraction/{fw}/{ex}/extracted.ttl"
        g_ast = load_graph(ast_ttl)
        if g_ast is None:
            continue

        run_paths: list[Path] = []
        for r in range(1, N_RUNS + 1):
            out = OUT_ROOT / f"run{r}" / fw / ex / "extracted.ttl"
            if out.exists():
                print(f"  run {r}: already exists, skipping call")
            else:
                print(f"  run {r}: calling LLM...")
                try:
                    run_llm_extraction(
                        source_dir=src,
                        output_path=out,
                        instance_namespace=f"http://oscin.example.org/{fw}/{ex}#",
                        provider=PROVIDER,
                        model=MODEL,
                    )
                except Exception as e:
                    print(f"  run {r} failed: {e}")
                    continue
            # Prefer the rebased TTL (instance vs schema namespace separated)
            rebased = out.parent / "extracted_rebased.ttl"
            run_paths.append(rebased if rebased.exists() else out)

        # load LLM graphs
        llm_graphs: dict[int, Graph] = {}
        for i, p in enumerate(run_paths, start=1):
            g = load_graph(p)
            if g is not None:
                llm_graphs[i] = g

        # AST intrinsic
        ast_intr = intrinsic(g_ast)

        # per-run intrinsic + LLM-vs-AST pairwise
        per_run = []
        for i, g in llm_graphs.items():
            row = {"run": i, **intrinsic(g), "vs_ast": pair_metrics(g_ast, g)}
            per_run.append(row)

        # within-LLM reproducibility (pairwise across runs)
        repro = []
        for (i, gi), (j, gj) in combinations(llm_graphs.items(), 2):
            repro.append({"pair": f"{i}vs{j}", **pair_metrics(gi, gj)})

        def avg(rows, key):
            vals = [r[key] for r in rows if r.get(key) is not None]
            return mean(vals) if vals else None

        def std(rows, key):
            vals = [r[key] for r in rows if r.get(key) is not None]
            return pstdev(vals) if len(vals) > 1 else 0.0

        agg_vs_ast = {
            level: {
                "mean": avg([r["vs_ast"] for r in per_run], f"{level}_f1"),
                "std": std([r["vs_ast"] for r in per_run], f"{level}_f1"),
            }
            for level in ("individual", "property", "triple")
        }
        agg_repro = {
            level: {
                "mean": avg(repro, f"{level}_f1"),
                "std": std(repro, f"{level}_f1"),
            }
            for level in ("individual", "property", "triple")
        }
        agg_intr = {
            "triples_mean": avg(per_run, "intrinsic_triples"),
            "triples_std": std(per_run, "intrinsic_triples"),
            "individuals_mean": avg(per_run, "intrinsic_individuals"),
            "individuals_std": std(per_run, "intrinsic_individuals"),
        }

        summary["examples"].append({
            "framework": fw,
            "example": ex,
            "ast_intrinsic": ast_intr,
            "llm_runs": per_run,
            "reproducibility_pairs": repro,
            "agg_vs_ast": agg_vs_ast,
            "agg_repro": agg_repro,
            "agg_intrinsic": agg_intr,
        })

    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_ROOT / 'summary.json'}")

    # markdown
    lines = ["# LLM baseline (provider=%s, model=%s, N=%d runs)" % (PROVIDER, MODEL, N_RUNS), ""]
    lines.append("## LLM vs AST pairwise F1 (mean ± std over runs)")
    lines.append("")
    lines.append("| framework | example | ind F1 | prop F1 | triple F1 | LLM triples (mean±std) | AST triples |")
    lines.append("|---|---|---|---|---|---|---|")
    for ex in summary["examples"]:
        a = ex["agg_vs_ast"]
        i = ex["agg_intrinsic"]
        ast_t = ex["ast_intrinsic"]["intrinsic_triples"]
        def fmt(d):
            return f"{d['mean']:.3f}±{d['std']:.3f}" if d["mean"] is not None else "—"
        lines.append(
            f"| {ex['framework']} | {ex['example']} | {fmt(a['individual'])} | {fmt(a['property'])} | {fmt(a['triple'])} | {i['triples_mean']:.0f}±{i['triples_std']:.0f} | {ast_t} |"
        )
    lines.append("")
    lines.append("## LLM reproducibility (pairwise F1 between independent runs, mean ± std)")
    lines.append("")
    lines.append("| framework | example | ind F1 | prop F1 | triple F1 |")
    lines.append("|---|---|---|---|---|")
    for ex in summary["examples"]:
        r = ex["agg_repro"]
        def fmt(d):
            return f"{d['mean']:.3f}±{d['std']:.3f}" if d["mean"] is not None else "—"
        lines.append(f"| {ex['framework']} | {ex['example']} | {fmt(r['individual'])} | {fmt(r['property'])} | {fmt(r['triple'])} |")
    (OUT_ROOT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT_ROOT / 'summary.md'}")


if __name__ == "__main__":
    main()
