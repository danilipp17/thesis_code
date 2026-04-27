"""
Re-base LLM-extracted TTL files: any URI in the AGENTOSCIN namespace
that is NOT a defined class/property in the schema is rewritten to an
instance namespace, so the existing intrinsic / pairwise evaluator
treats it as ABox.

Used as a pre-processing step before evaluation, since gpt-4o tends
to ignore the `{{instance_namespace}}` placeholder and put both
schema and individuals under `:`.
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL

AO = "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
INSTANCE_NS = "http://oscin.example.org/llm-instance#"
ROOT = Path(__file__).resolve().parent.parent


def schema_uris(ontology_ttl: Path) -> set[str]:
    g = Graph()
    g.parse(str(ontology_ttl), format="turtle")
    schema = set()
    schema_types = {OWL.Class, RDFS.Class, OWL.ObjectProperty,
                    OWL.DatatypeProperty, OWL.AnnotationProperty,
                    RDF.Property}
    for s, p, o in g.triples((None, RDF.type, None)):
        if o in schema_types and isinstance(s, URIRef) and str(s).startswith(AO):
            schema.add(str(s))
    return schema


def rebase_graph(g_in: Graph, schema: set[str]) -> Graph:
    g_out = Graph()
    for prefix, ns in g_in.namespaces():
        g_out.bind(prefix, ns)
    g_out.bind("inst", INSTANCE_NS)

    def rewrite(node):
        if isinstance(node, URIRef) and str(node).startswith(AO) and str(node) not in schema:
            return URIRef(INSTANCE_NS + str(node).replace(AO, ""))
        return node

    for s, p, o in g_in:
        g_out.add((rewrite(s), rewrite(p), rewrite(o)))
    return g_out


def main() -> None:
    schema = schema_uris(ROOT / "ontology/agentoscin.ttl")
    print(f"schema URIs: {len(schema)}")
    src_root = ROOT / "output/llm_baseline"
    for ttl in src_root.rglob("extracted.ttl"):
        if "_rebased" in ttl.parts:
            continue
        def try_parse(text: str) -> Graph | None:
            try:
                gg = Graph(); gg.parse(data=text, format="turtle")
                return gg
            except Exception:
                return None

        text = ttl.read_text(encoding="utf-8")
        g = try_parse(text)
        if g is None:
            import re
            # repair 1: inject missing standard prefixes
            std_prefixes = []
            if "@prefix rdf:" not in text and "@prefix\trdf:" not in text:
                std_prefixes.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
            if "@prefix rdfs:" not in text:
                std_prefixes.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
            if "@prefix xsd:" not in text:
                std_prefixes.append("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
            if "@prefix owl:" not in text:
                std_prefixes.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
            if std_prefixes:
                text2 = "\n".join(std_prefixes) + "\n" + text
                g = try_parse(text2)
                if g is not None:
                    print(f"  repaired (added prefixes) {ttl.relative_to(ROOT)}")
                    text = text2
            if g is None:
                # repair 2: missing '.' before new subject
                text2 = re.sub(r";\s*\n\s*\n(?=[:a-zA-Z_])", ".\n\n", text)
                text2 = re.sub(r";\s*\n\s*\n###", ".\n\n###", text2)
                g = try_parse(text2)
                if g is not None:
                    print(f"  repaired (statement terminator) {ttl.relative_to(ROOT)}")
            if g is None:
                print(f"  parse failed {ttl.relative_to(ROOT)}")
                continue
        g2 = rebase_graph(g, schema)
        out = ttl.parent / "extracted_rebased.ttl"
        g2.serialize(destination=str(out), format="turtle")
        print(f"  rebased {ttl.relative_to(ROOT)}  ({len(g2)} triples)")


if __name__ == "__main__":
    main()
