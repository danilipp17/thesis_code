# Parallel-corpus evaluation

A small hand-curated benchmark for evaluating OSCIN extraction and generation
fidelity across all three target frameworks (CrewAI, LangGraph, AutoGen).

## Design

Each **family** is a single scenario implemented in all three frameworks:

* one variant is the **original** (authored against the framework's idioms);
* the other two are **manual ports** that reproduce the same observable
  behaviour by inspection (no automated equivalence check).

Each variant ships with a **hand-authored `ground_truth.ttl`** — a framework-
flavoured ABox over the AgentOSCIN ontology. The TTLs are deliberately *not*
identical across the three: framework idioms (CrewAI's Task objects, LangGraph's
StateGraph workflow steps, AutoGen's RoundRobin team) are preserved, which is
itself a finding of the thesis.

## Layout

```
examples/parallel/<family>/
    README.md                 (per-family scenario notes)
    <framework>/
        source_files          symlink to the canonical source tree
        ground_truth.ttl      hand-authored ABox
```

The `source_files` entry is a symlink so that the existing per-framework
`examples/<fw>/<name>/` trees remain the single source of truth for the source
code; only the new ground-truth TTLs live under `examples/parallel/`.

## Families

| family       | origin    | scenario                                          |
|--------------|-----------|---------------------------------------------------|
| tech-blog    | CrewAI    | linear 3-agent pipeline (researcher→writer→editor) |
| joke         | LangGraph | single-node generator with refinement loop         |
| code-review  | AutoGen   | multi-agent group chat (RoundRobin team)           |

## Evaluations

Driven from the GUI's **Parallel corpus** tab. Two experiments per cell:

1. **Extraction fidelity** — OSCIN extracts the source → compared against the
   hand-authored `ground_truth.ttl` via `ttl_pairwise` (triple / property /
   individual F1, aligned-triple F1, literal overlap) and `ttl_fuzzy_match`.
2. **Generation fidelity** — OSCIN generates source from `ground_truth.ttl`
   into the same framework → compared against the original `source_files/`
   via `ast_diff` and `syntax_validity`.

No `mapping_conformance` and no `execution_trace` — see thesis for rationale.
