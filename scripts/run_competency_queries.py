"""
run_competency_queries.py
=========================
Load ontology/combined_kg.ttl and execute every query in
ontology/competency_queries.rq. Print the number of result rows per
CQ and a short preview, so you can verify each query is well-formed
and returns sensible answers against the six-system knowledge graph.

Run with:
    python scripts/run_competency_queries.py
    python scripts/run_competency_queries.py --preview 10        # more rows
    python scripts/run_competency_queries.py --only CQ-23        # one query
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from textwrap import shorten

from rdflib import Graph
from rdflib.query import Result

ROOT = Path(__file__).resolve().parent.parent
KG = ROOT / "ontology" / "combined_kg.ttl"
RQ = ROOT / "ontology" / "competency_queries.rq"


def _split_queries(text: str) -> list[tuple[str, str, str]]:
    """Parse the .rq file into [(cq_id, header, query_text)] preserving order."""
    # The file is a sequence of comment-headed blocks ending at the next
    # ``# CQ-N`` marker or EOF. Everything before the first CQ marker is
    # the prefix block which we keep separately and inject into each query.
    text = text.replace("\r\n", "\n")
    marker = re.compile(r"^# CQ-(\d+)\s*\(([^)]*)\)\s*—\s*(.+)$", re.MULTILINE)
    matches = list(marker.finditer(text))
    if not matches:
        return []
    # PREFIX block lives before the first marker
    prefix = ""
    for line in text[: matches[0].start()].splitlines():
        s = line.strip()
        if s.startswith("PREFIX"):
            prefix += line + "\n"
    out: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        cq_id = f"CQ-{m.group(1)}"
        header = m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        # strip leading dashes line and stop at the next "# =====" banner
        body = re.split(r"^# ====+$", body, flags=re.MULTILINE)[0]
        # remove leading '# -----' rule line and blank lines
        lines = []
        for ln in body.splitlines():
            if ln.strip().startswith("# -----"):
                continue
            lines.append(ln)
        sparql = prefix + "\n" + "\n".join(lines).strip() + "\n"
        out.append((cq_id, header, sparql))
    return out


def _row_summary(row, max_len: int = 60) -> str:
    """Short textual rendering of one SPARQL row."""
    parts = []
    for var in row.labels:
        v = row[var]
        if v is None:
            parts.append(f"{var}=∅")
            continue
        s = str(v)
        # strip long IRIs to their local name
        if "#" in s:
            s = s.split("#", 1)[1]
        elif "/" in s and s.startswith("http"):
            s = s.rsplit("/", 1)[1]
        s = shorten(s, width=max_len, placeholder="…")
        parts.append(f"{var}={s}")
    return "  ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=int, default=3,
                    help="Number of result rows to show per query.")
    ap.add_argument("--only", default=None,
                    help='Run only the named query, e.g. "CQ-23".')
    args = ap.parse_args()

    print(f"Loading KG: {KG}")
    g = Graph()
    g.parse(str(KG), format="turtle")
    print(f"  {len(g)} triples loaded")

    queries = _split_queries(RQ.read_text(encoding="utf-8"))
    print(f"Found {len(queries)} queries\n")

    summary: list[tuple[str, int]] = []
    for cq_id, header, sparql in queries:
        if args.only and cq_id != args.only:
            continue
        print(f"── {cq_id}: {header}")
        try:
            res: Result = g.query(sparql)
            rows = list(res)
        except Exception as e:
            print(f"   QUERY ERROR: {type(e).__name__}: {e}")
            summary.append((cq_id, -1))
            print()
            continue
        summary.append((cq_id, len(rows)))
        print(f"   rows: {len(rows)}")
        for r in rows[: args.preview]:
            print(f"     • {_row_summary(r)}")
        if len(rows) > args.preview:
            print(f"     … (+{len(rows) - args.preview} more)")
        print()

    if not args.only:
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for cq_id, n in summary:
            tag = "ok" if n > 0 else ("empty" if n == 0 else "ERROR")
            print(f"  {cq_id:6s}  rows={n:>4d}   {tag}")
        nonzero = sum(1 for _, n in summary if n > 0)
        empty = sum(1 for _, n in summary if n == 0)
        err = sum(1 for _, n in summary if n < 0)
        print(f"\n  {nonzero}/{len(summary)} queries return results; "
              f"{empty} empty; {err} errors")


if __name__ == "__main__":
    main()
