"""
build_combined_kg.py
====================
Produce a single self-contained Turtle file that holds the agentO TBox,
the agentoscin TBox and the ABoxes of the six original-framework systems
from the parallel corpus, all in one graph. The file is queryable
out-of-the-box; nothing needs to be imported externally.

Per-system instance namespaces are rewritten to a canonical
``http://example.org/parallel/<family>_<framework>#`` so that no two
individuals collide on local name across systems.

Output: ontology/combined_kg.ttl
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from rdflib import Graph, URIRef, Namespace

ROOT = Path(__file__).resolve().parent.parent
ONT_DIR = ROOT / "ontology"
EX_DIR = ROOT / "examples" / "parallel"

# The six families with their original framework (per the corpus table)
ORIGINALS = [
    ("joke",                   "langgraph"),
    ("code-review",            "autogen"),
    ("tech-blog",              "crewai"),
    ("meeting-assistant-flow", "crewai"),
    ("travel-planning",        "autogen"),
    ("react",                  "langgraph"),
]

# Short prefix per system (used in the serialised TTL prefix block)
PREFIXES = {
    ("joke", "langgraph"):                   "joke_lg",
    ("code-review", "autogen"):              "cr_ag",
    ("tech-blog", "crewai"):                 "tb_cr",
    ("meeting-assistant-flow", "crewai"):    "ma_cr",
    ("travel-planning", "autogen"):          "tp_ag",
    ("react", "langgraph"):                  "react_lg",
}


def canonical_ns(family: str, fw: str) -> str:
    """Canonical instance namespace for a given (family, framework)."""
    return f"http://example.org/parallel/{family.replace('-', '_')}_{fw}#"


def rewrite_namespace(g_in: Graph, old_ns: str, new_ns: str) -> Graph:
    """Return a new graph where every IRI starting with old_ns is rewritten to new_ns."""
    g_out = Graph()
    for prefix, ns in g_in.namespaces():
        if str(ns).startswith("http://example.org/"):
            continue  # we'll bind the new instance prefix later
        g_out.bind(prefix, ns)
    def fix(node):
        if isinstance(node, URIRef) and str(node).startswith(old_ns):
            return URIRef(new_ns + str(node)[len(old_ns):])
        return node
    for s, p, o in g_in:
        g_out.add((fix(s), fix(p), fix(o)))
    return g_out


def detect_instance_ns(g: Graph) -> str | None:
    """The instance namespace is the value bound to ``ex`` in the original file
    (the GTs all use ``@prefix ex: <...> .``)."""
    for prefix, ns in g.namespaces():
        if prefix == "ex":
            return str(ns)
    return None


def load_and_rewrite(family: str, fw: str) -> tuple[Graph, str, str]:
    """Load a GT, rewrite its instance namespace, return (graph, new_ns, short_prefix)."""
    path = EX_DIR / family / fw / "ground_truth.ttl"
    g = Graph()
    g.parse(str(path), format="turtle")
    old_ns = detect_instance_ns(g)
    if old_ns is None:
        raise RuntimeError(f"no ex: prefix in {path}")
    new_ns = canonical_ns(family, fw)
    g2 = rewrite_namespace(g, old_ns, new_ns)
    # also rewrite the ontology header IRI (the bare URI without #)
    old_ont = old_ns.rstrip("#")
    new_ont = new_ns.rstrip("#")
    def fix(node):
        if isinstance(node, URIRef) and str(node) == old_ont:
            return URIRef(new_ont)
        return node
    g3 = Graph()
    for prefix, ns in g2.namespaces():
        g3.bind(prefix, ns)
    for s, p, o in g2:
        g3.add((fix(s), fix(p), fix(o)))
    return g3, new_ns, PREFIXES[(family, fw)]


def main() -> None:
    out = Graph()
    # Bind canonical prefixes
    out.bind("agento", "http://www.w3id.org/agentic-ai/onto#")
    out.bind("agentoscin",
             "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/")
    out.bind("owl", "http://www.w3.org/2002/07/owl#")
    out.bind("xsd", "http://www.w3.org/2001/XMLSchema#")
    out.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
    out.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")

    # ----- TBox: agentO + agentoscin -----
    print("Loading TBox: agentO.ttl")
    out.parse(str(ONT_DIR / "agentO.ttl"), format="turtle")
    print("Loading TBox: agentoscin.ttl")
    out.parse(str(ONT_DIR / "agentoscin.ttl"), format="turtle")

    # ----- ABox: 6 original systems -----
    for family, fw in ORIGINALS:
        print(f"Loading ABox: {family}/{fw}")
        g_sys, ns, short = load_and_rewrite(family, fw)
        for s, p, o in g_sys:
            out.add((s, p, o))
        out.bind(short, Namespace(ns))

    # ----- ABox: synthetic feature-demo system -----
    print("Loading ABox: feature_demo (synthetic)")
    g_demo = Graph()
    g_demo.parse(str(ONT_DIR / "feature_demo.ttl"), format="turtle")
    for s, p, o in g_demo:
        out.add((s, p, o))
    out.bind("demo", "http://example.org/demo/feature_demo#")

    out_path = ONT_DIR / "combined_kg.ttl"
    out.serialize(destination=str(out_path), format="turtle")
    # Add a top-of-file banner
    text = out_path.read_text(encoding="utf-8")
    banner = (
        "# ============================================================\n"
        "# combined_kg.ttl\n"
        "# Self-contained knowledge graph for competency-question queries.\n"
        "# Contents:\n"
        "#   - TBox: agentO (parent ontology) + agentoscin (extension)\n"
        "#   - ABox: six original-framework systems from the parallel corpus\n"
        "#       joke              (LangGraph)  prefix joke_lg:\n"
        "#       code-review       (AutoGen)    prefix cr_ag:\n"
        "#       tech-blog         (CrewAI)     prefix tb_cr:\n"
        "#       meeting-assistant (CrewAI)     prefix ma_cr:\n"
        "#       travel-planning   (AutoGen)    prefix tp_ag:\n"
        "#       react             (LangGraph)  prefix react_lg:\n"
        "#   - ABox: one synthetic system exercising ontology features\n"
        "#     that the corpus does not populate (reasoning patterns,\n"
        "#     memory bindings, guardrails, human checkpoints, …)\n"
        "#       feature_demo                   prefix demo:\n"
        "# Generated by scripts/build_combined_kg.py\n"
        "# ============================================================\n\n"
    )
    out_path.write_text(banner + text, encoding="utf-8")
    print(f"\nWrote {out_path}  ({len(out)} triples)")


if __name__ == "__main__":
    main()
