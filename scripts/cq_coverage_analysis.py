"""
cq_coverage_analysis.py
=======================
For each of the 35 competency questions, classify coverage as
FULL, PARTIAL or NONE under two ontology configurations:

    agentoscin = agentO + agentoscin extension  (the full ontology)
    agentO     = parent ontology only

Two coverage dimensions per CQ:

  Ontology-level coverage
    FULL    — every property/class the query needs is declared in the
              ontology (so the query is well-typed and can in principle
              return populated answers).
    PARTIAL — some of the requested fields can be answered but at least
              one concept needed by the question is missing from the
              ontology, so the answer is incomplete by construction.
    NONE    — the central concept of the question is not representable
              in the ontology at all.

  Data-level coverage (against the seven-system knowledge graph)
    FULL    — query returns rows AND every projected variable is bound
              on every row.
    PARTIAL — query returns rows but at least one projected variable
              is unbound on some row (e.g. an OPTIONAL field missing).
    NONE    — query returns zero rows.

Ontology coverage is judged statically (does the ontology declare the
needed properties); data coverage is judged dynamically (does the query
return rows against ontology/combined_kg.ttl).
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parent.parent
KG = ROOT / "ontology" / "combined_kg.ttl"
RQ = ROOT / "ontology" / "competency_queries.rq"

AGENTO_NS = "http://www.w3id.org/agentic-ai/onto#"
AGENTOSCIN_NS = "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"


# ---------------------------------------------------------------------
# Static ontology coverage classification (per CQ)
# ---------------------------------------------------------------------
# Each CQ is annotated with the agentO-only verdict and a short reason.
# agentoscin is FULL on every CQ by construction — it is the ontology
# that hosts all 35 queries. The interesting comparison is what agentO
# can answer on its own.

AGENTO_VERDICT: dict[str, tuple[str, str]] = {
    # CQ:  (FULL/PARTIAL/NONE, reason)
    "CQ-1":  ("PARTIAL", "agentO has LLMAgent but no AgenticSystem/containsAgent — agents listable, not scopable to a system"),
    "CQ-2":  ("FULL",    "agentID and agentRole are in agentO"),
    "CQ-3":  ("NONE",    "agentType is agentoscin-only (agentO has HumanAgent class only)"),
    "CQ-4":  ("FULL",    "agentPrompt, taskPrompt, performedByAgent all in agentO"),
    "CQ-5":  ("NONE",    "hasDirectiveFunction is agentoscin-only"),
    "CQ-6":  ("FULL",    "promptInstruction, promptContext, promptOutputIndicator all in agentO"),
    "CQ-7":  ("FULL",    "agentID, agentRole, useLanguageModel, agentPrompt, hasAgentGoal all in agentO"),
    "CQ-8":  ("NONE",    "agentType, employsReasoningPattern, hasMemoryBinding all agentoscin-only"),
    "CQ-9":  ("PARTIAL", "agentO has HumanAgent class but no agentType for proxy/role classification"),
    "CQ-10": ("NONE",    "no worker/manager distinction in agentO"),
    "CQ-11": ("PARTIAL", "Task and taskPrompt in agentO; hasDescription is agentoscin-only"),
    "CQ-12": ("FULL",    "Task and performedByAgent in agentO"),
    "CQ-13": ("NONE",    "hasDelegationStrategy is agentoscin-only"),
    "CQ-14": ("NONE",    "dependsOn is agentoscin-only"),
    "CQ-15": ("NONE",    "dependsOn and hasDependencyType are agentoscin-only"),
    "CQ-16": ("NONE",    "hasExpectedOutput is agentoscin-only"),
    "CQ-17": ("NONE",    "hasOutputSchema and Schema class are agentoscin-only"),
    "CQ-18": ("NONE",    "Team in agentO but employsCoordinationPattern is agentoscin-only"),
    "CQ-19": ("FULL",    "Team and hasAgentMember in agentO"),
    "CQ-20": ("PARTIAL", "members listable in agentO; coordination pattern is agentoscin-only"),
    "CQ-21": ("NONE",    "TerminationCondition is agentoscin-only"),
    "CQ-22": ("NONE",    "containsTeam/orchestratesTeam are agentoscin-only"),
    "CQ-23": ("FULL",    "WorkflowPattern, hasWorkflowStep, stepOrder, nextStep all in agentO"),
    "CQ-24": ("NONE",    "ConditionalStep, hasEdgeMapping, hasRoutingLogic agentoscin-only"),
    "CQ-25": ("NONE",    "hasReasoningEnabled is agentoscin-only"),
    "CQ-26": ("NONE",    "ReasoningPattern class hierarchy is agentoscin-only"),
    "CQ-27": ("NONE",    "hasReasoningOrigin is agentoscin-only"),
    "CQ-28": ("PARTIAL", "Memory class in agentO but no MemoryBinding/scope semantics"),
    "CQ-29": ("PARTIAL", "Memory listable in agentO; hasPersistenceScope is agentoscin-only"),
    "CQ-30": ("PARTIAL", "Tool in agentO but title via agentoscin (rdfs:label would suffice)"),
    "CQ-31": ("PARTIAL", "Tool exists in agentO; hasInputSchema is agentoscin-only"),
    "CQ-32": ("FULL",    "agentToolUsage is in agentO"),
    "CQ-33": ("PARTIAL", "agentO has generic toolUsage but no task-level binding semantics"),
    "CQ-34": ("NONE",    "Guardrail class agentoscin-only"),
    "CQ-35": ("NONE",    "HumanCheckpoint agentoscin-only (agentO has HumanAgent class)"),
}


# ---------------------------------------------------------------------
# SPARQL query parsing (same as run_competency_queries.py)
# ---------------------------------------------------------------------

def _split_queries(text: str) -> list[tuple[str, str, str]]:
    text = text.replace("\r\n", "\n")
    marker = re.compile(r"^# CQ-(\d+)\s*\(([^)]*)\)\s*—\s*(.+)$", re.MULTILINE)
    matches = list(marker.finditer(text))
    if not matches:
        return []
    prefix = ""
    for line in text[: matches[0].start()].splitlines():
        if line.strip().startswith("PREFIX"):
            prefix += line + "\n"
    out = []
    for i, m in enumerate(matches):
        cq_id = f"CQ-{m.group(1)}"
        header = m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = re.split(r"^# ====+$", text[start:end], flags=re.MULTILINE)[0]
        body = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith("# -----"))
        out.append((cq_id, header, prefix + "\n" + body.strip() + "\n"))
    return out


def classify_data_coverage(rows) -> str:
    """FULL = rows with every projected var bound on every row.
       PARTIAL = rows but at least one projected var unbound somewhere.
       NONE = zero rows."""
    if not rows:
        return "NONE"
    for r in rows:
        for var in r.labels:
            if r[var] is None:
                return "PARTIAL"
    return "FULL"


def main() -> None:
    g = Graph()
    g.parse(str(KG), format="turtle")

    queries = _split_queries(RQ.read_text(encoding="utf-8"))

    # Per-CQ results
    rows = []
    for cq_id, header, sparql in queries:
        res = list(g.query(sparql))
        data_cov = classify_data_coverage(res)
        ont_full = "FULL"  # by construction
        ont_O, reason = AGENTO_VERDICT.get(cq_id, ("?", "?"))
        rows.append({
            "cq": cq_id,
            "header": header,
            "rows": len(res),
            "data_coverage": data_cov,
            "agentoscin_coverage": ont_full,
            "agentO_coverage": ont_O,
            "reason_agentO": reason,
        })

    # ----- print per-CQ table -----
    print(f"{'CQ':6s} {'rows':>5s}  {'data':>7s}  {'agentoscin':>10s}  {'agentO':>8s}  reason (agentO)")
    print("-" * 110)
    for r in rows:
        print(f"{r['cq']:6s} {r['rows']:>5d}  {r['data_coverage']:>7s}  "
              f"{r['agentoscin_coverage']:>10s}  {r['agentO_coverage']:>8s}  {r['reason_agentO']}")

    # ----- summary -----
    print()
    def tally(field):
        c = defaultdict(int)
        for r in rows:
            c[r[field]] += 1
        return dict(c)
    print("=== Summary tallies (35 CQs) ===")
    print(f"  agentoscin ontology coverage : {tally('agentoscin_coverage')}")
    print(f"  agentO     ontology coverage : {tally('agentO_coverage')}")
    print(f"  data coverage (corpus + demo): {tally('data_coverage')}")

    # ----- per-requirement aggregation -----
    REQ_MAP = {
        "CQ-1":"R1","CQ-2":"R1","CQ-3":"R1",
        "CQ-4":"R2","CQ-5":"R2",
        "CQ-6":"R3",
        "CQ-7":"R4","CQ-8":"R4",
        "CQ-9":"R5","CQ-10":"R5",
        "CQ-11":"R6",
        "CQ-12":"R7","CQ-13":"R7",
        "CQ-14":"R8","CQ-15":"R8",
        "CQ-16":"R9","CQ-17":"R9",
        "CQ-18":"R10",
        "CQ-19":"R11","CQ-20":"R11",
        "CQ-21":"R12",
        "CQ-22":"R13",
        "CQ-23":"R14","CQ-24":"R14",
        "CQ-25":"R15","CQ-26":"R15","CQ-27":"R15",
        "CQ-28":"R16",
        "CQ-29":"R17",
        "CQ-30":"R18","CQ-31":"R18",
        "CQ-32":"R19","CQ-33":"R19",
        "CQ-34":"R20",
        "CQ-35":"R21",
    }
    def req_verdict(cq_subset, key):
        verdicts = [r[key] for r in cq_subset]
        if all(v == "FULL" for v in verdicts): return "FULL"
        if all(v == "NONE" for v in verdicts): return "NONE"
        return "PARTIAL"
    print()
    print("=== Per-requirement (R1–R21) coverage ===")
    print(f"  {'req':5s}  {'CQs':<28s} {'agentoscin':>10s}  {'agentO':>8s}")
    by_req = defaultdict(list)
    for r in rows:
        by_req[REQ_MAP[r["cq"]]].append(r)
    for req in [f"R{i}" for i in range(1, 22)]:
        subset = by_req[req]
        cqs = ",".join(r["cq"] for r in subset)
        print(f"  {req:5s}  {cqs:<28s} "
              f"{req_verdict(subset,'agentoscin_coverage'):>10s}  "
              f"{req_verdict(subset,'agentO_coverage'):>8s}")


if __name__ == "__main__":
    main()
