"""
verify_three_experiments.py
===========================
End-to-end re-run of the three transformation experiments on the parallel
corpus, using the existing metric code unchanged. Writes everything into a
fresh ``output/eval_verify_v2/`` so prior results stay intact.

Experiments
-----------
1. Extraction       — extract source -> compare against hand-authored GT_S
2. Generation       — generate(GT_S, target=S) -> AST diff vs hand-authored source_S
3. Cross-fw RT      — generate(GT_S, target=T) -> extract_T -> compare against GT_T

Outputs
-------
output/eval_verify_v2/extraction/<family>__<fw>/{extracted.ttl, metrics.json}
output/eval_verify_v2/generation/<family>__<fw>/{generated/, ast_diff.json}
output/eval_verify_v2/cross/<family>__<S>__to__<T>/{generated/, reextracted.ttl, metrics.json}
output/eval_verify_v2/summary.json
output/eval_verify_v2/summary.md
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from statistics import mean

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oscin.evaluator import compute_pairwise  # noqa: E402
from evaluation.metrics import ast_diff, syntax_validity  # noqa: E402
from evaluation.pipelines._common import (  # noqa: E402
    default_namespace, default_system_name, run_oscin,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

FAMILIES = ["joke", "code-review", "tech-blog",
            "meeting-assistant-flow", "travel-planning", "react"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

OUT = ROOT / "output" / "eval_verify"


def _gt(family: str, fw: str) -> Path:
    return ROOT / "examples" / "parallel" / family / fw / "ground_truth.ttl"


def _src(family: str, fw: str) -> Path:
    return ROOT / "examples" / "parallel" / family / fw / "source_files"


def load(p: Path) -> Graph | None:
    if not p.exists():
        return None
    g = Graph()
    try:
        g.parse(str(p), format="turtle")
        return g
    except Exception as e:
        print(f"  parse failed for {p}: {e}")
        return None


def abox_metrics(ref: Graph, cand: Graph) -> dict:
    m = compute_pairwise(ref, cand)
    return {
        "triple_f1": m.triple_f1,
        "aligned_triple_f1": m.aligned_triple_f1,
        "individual_f1": m.individual_f1,
        "property_f1": m.property_f1,
        "literal_overlap": m.literal_overlap,
    }


# --------------------------------------------------------------------- #
# 1. Extraction
# --------------------------------------------------------------------- #

def run_extraction() -> list[dict]:
    print("\n[1/3] Extraction")
    rows: list[dict] = []
    for family in FAMILIES:
        for fw in FRAMEWORKS:
            cell_id = f"{family}__{fw}"
            print(f"  {cell_id}", end=" ", flush=True)
            src = _src(family, fw)
            gt = _gt(family, fw)
            if not src.is_dir() or not gt.is_file():
                print("SKIP (missing files)")
                continue
            cell_dir = OUT / "extraction" / cell_id
            cell_dir.mkdir(parents=True, exist_ok=True)
            extracted = cell_dir / "extracted.ttl"
            ns = default_namespace(family)
            system_name = default_system_name(family)
            run_oscin([
                "extract", str(src),
                "--framework", fw,
                "--system-name", system_name,
                "--namespace", ns,
                "--output", str(extracted),
                "--no-report",
            ])
            g_ref = load(gt); g_cand = load(extracted)
            if g_ref is None or g_cand is None:
                print("PARSE FAIL")
                continue
            m = abox_metrics(g_ref, g_cand)
            (cell_dir / "metrics.json").write_text(json.dumps(m, indent=2))
            rows.append({"family": family, "framework": fw, **m})
            print(f"triple={m['triple_f1']:.3f} aligned={m['aligned_triple_f1']:.3f} "
                  f"ind={m['individual_f1']:.3f} prop={m['property_f1']:.3f} "
                  f"lit={m['literal_overlap']:.3f}")
    return rows


# --------------------------------------------------------------------- #
# 2. Generation
# --------------------------------------------------------------------- #

def _ast_diff(gt_src: Path, gen_dir: Path) -> dict:
    res = ast_diff.compute(gt_src, gen_dir)
    overall = res.get("overall", {})
    syn = syntax_validity.compute(gen_dir)
    return {
        "ast_precision": overall.get("precision"),
        "ast_recall": overall.get("recall"),
        "ast_f1": overall.get("f1"),
        "parse_rate": syn.get("syntax_rate"),
        "import_rate": syn.get("import_rate"),
    }


def run_generation() -> list[dict]:
    print("\n[2/3] Generation")
    rows: list[dict] = []
    for family in FAMILIES:
        for fw in FRAMEWORKS:
            cell_id = f"{family}__{fw}"
            print(f"  {cell_id}", end=" ", flush=True)
            gt = _gt(family, fw); ref_src = _src(family, fw)
            if not gt.is_file() or not ref_src.is_dir():
                print("SKIP (missing files)")
                continue
            cell_dir = OUT / "generation" / cell_id
            gen_dir = cell_dir / "generated"
            gen_dir.parent.mkdir(parents=True, exist_ok=True)
            run_oscin([
                "generate", str(gt),
                "--target-framework", fw,
                "--output-dir", str(gen_dir),
            ])
            m = _ast_diff(ref_src, gen_dir)
            (cell_dir / "ast_diff.json").write_text(json.dumps(m, indent=2))
            rows.append({"family": family, "framework": fw, **m})
            def _f(v): return f"{v:.3f}" if isinstance(v, (int, float)) else "—"
            print(f"ast_p={_f(m['ast_precision'])} ast_r={_f(m['ast_recall'])} "
                  f"ast_f1={_f(m['ast_f1'])} parse={_f(m['parse_rate'])}")
    return rows


# --------------------------------------------------------------------- #
# 3. Cross-framework round-trip
# --------------------------------------------------------------------- #

def run_crossfw() -> list[dict]:
    print("\n[3/3] Cross-framework round-trip")
    rows: list[dict] = []
    for family in FAMILIES:
        for src_fw in FRAMEWORKS:
            for tgt_fw in FRAMEWORKS:
                if src_fw == tgt_fw:
                    continue
                cell_id = f"{family}__{src_fw}__to__{tgt_fw}"
                print(f"  {cell_id}", end=" ", flush=True)
                gt_src = _gt(family, src_fw)
                gt_tgt = _gt(family, tgt_fw)
                ref_src_dir = _src(family, tgt_fw)
                if not (gt_src.is_file() and gt_tgt.is_file() and ref_src_dir.is_dir()):
                    print("SKIP (missing files)")
                    continue
                cell_dir = OUT / "cross" / cell_id
                gen_dir = cell_dir / "generated"
                gen_dir.parent.mkdir(parents=True, exist_ok=True)
                # generate from source GT, targeting tgt framework
                run_oscin([
                    "generate", str(gt_src),
                    "--target-framework", tgt_fw,
                    "--output-dir", str(gen_dir),
                ])
                # re-extract with tgt extractor
                reextracted = cell_dir / "reextracted.ttl"
                ns = default_namespace(family)
                system_name = default_system_name(family)
                try:
                    run_oscin([
                        "extract", str(gen_dir),
                        "--framework", tgt_fw,
                        "--system-name", system_name,
                        "--namespace", ns,
                        "--output", str(reextracted),
                        "--no-report",
                    ])
                except Exception as e:
                    print(f"REEXTRACT FAIL: {e}")
                    continue
                # ABox metrics: reextracted vs hand-authored target GT
                g_ref = load(gt_tgt); g_cand = load(reextracted)
                abox = abox_metrics(g_ref, g_cand) if (g_ref and g_cand) else None
                # AST diff: generated vs hand-authored target source
                ast = _ast_diff(ref_src_dir, gen_dir)
                row = {
                    "family": family, "src": src_fw, "tgt": tgt_fw,
                    **(abox or {k: None for k in (
                        "triple_f1", "aligned_triple_f1", "individual_f1",
                        "property_f1", "literal_overlap")}),
                    **ast,
                }
                (cell_dir / "metrics.json").write_text(json.dumps(row, indent=2))
                rows.append(row)
                print(f"triple={(row['triple_f1'] or 0):.3f} aligned={(row['aligned_triple_f1'] or 0):.3f} "
                      f"ind={(row['individual_f1'] or 0):.3f} ast={(row['ast_f1'] or 0):.3f}")
    return rows


# --------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------- #

def _mean(rows, key):
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return mean(vals) if vals else None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    extraction = run_extraction()
    generation = run_generation()
    crossfw = run_crossfw()

    summary = {
        "extraction": {
            "cells": extraction,
            "mean_triple_f1": _mean(extraction, "triple_f1"),
            "mean_aligned_triple_f1": _mean(extraction, "aligned_triple_f1"),
            "mean_individual_f1": _mean(extraction, "individual_f1"),
            "mean_property_f1": _mean(extraction, "property_f1"),
            "mean_literal_overlap": _mean(extraction, "literal_overlap"),
        },
        "generation": {
            "cells": generation,
            "mean_ast_precision": _mean(generation, "ast_precision"),
            "mean_ast_recall": _mean(generation, "ast_recall"),
            "mean_ast_f1": _mean(generation, "ast_f1"),
            "mean_parse_rate": _mean(generation, "parse_rate"),
        },
        "crossfw": {
            "cells": crossfw,
            "mean_triple_f1": _mean(crossfw, "triple_f1"),
            "mean_aligned_triple_f1": _mean(crossfw, "aligned_triple_f1"),
            "mean_individual_f1": _mean(crossfw, "individual_f1"),
            "mean_property_f1": _mean(crossfw, "property_f1"),
            "mean_literal_overlap": _mean(crossfw, "literal_overlap"),
            "mean_ast_f1": _mean(crossfw, "ast_f1"),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    # ----- markdown summary -----
    e = summary["extraction"]; g = summary["generation"]; c = summary["crossfw"]
    md = ["# eval_verify summary", ""]
    md.append("## Headline aggregates")
    md.append("")
    md.append("| experiment | triple | aligned | ind | prop | literal | ast |")
    md.append("|---|---|---|---|---|---|---|")
    md.append(
        f"| extraction (n={len(extraction)}) | "
        f"{e['mean_triple_f1']:.3f} | {e['mean_aligned_triple_f1']:.3f} | "
        f"{e['mean_individual_f1']:.3f} | {e['mean_property_f1']:.3f} | "
        f"{e['mean_literal_overlap']:.3f} | — |"
    )
    md.append(
        f"| generation (n={len(generation)}) | — | — | — | — | — | "
        f"{g['mean_ast_f1']:.3f} (parse {g['mean_parse_rate']:.3f}) |"
    )
    md.append(
        f"| crossfw (n={len(crossfw)}) | "
        f"{c['mean_triple_f1']:.3f} | {c['mean_aligned_triple_f1']:.3f} | "
        f"{c['mean_individual_f1']:.3f} | {c['mean_property_f1']:.3f} | "
        f"{c['mean_literal_overlap']:.3f} | {c['mean_ast_f1']:.3f} |"
    )
    md.append("")
    md.append("## Cross-fw per-direction means")
    md.append("")
    md.append("| src -> tgt | triple | aligned | ind | prop | literal | ast |")
    md.append("|---|---|---|---|---|---|---|")
    for s in FRAMEWORKS:
        for t in FRAMEWORKS:
            if s == t:
                continue
            sub = [r for r in crossfw if r["src"] == s and r["tgt"] == t]
            if not sub:
                continue
            md.append(
                f"| {s} -> {t} | "
                f"{_mean(sub, 'triple_f1'):.3f} | {_mean(sub, 'aligned_triple_f1'):.3f} | "
                f"{_mean(sub, 'individual_f1'):.3f} | {_mean(sub, 'property_f1'):.3f} | "
                f"{_mean(sub, 'literal_overlap'):.3f} | {_mean(sub, 'ast_f1'):.3f} |"
            )
    (OUT / "summary.md").write_text("\n".join(md) + "\n")
    print(f"\nWrote {OUT/'summary.json'} and {OUT/'summary.md'}")


if __name__ == "__main__":
    main()
