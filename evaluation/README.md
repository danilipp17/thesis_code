# `evaluation/` — OSCIN evaluation harness

Three **separate** evaluation pipelines, one shared metric registry, one
aggregator.

```
evaluation/
├── pipelines/
│   ├── extraction.py     source → TTL           (+ optional ground-truth compare)
│   ├── generation.py     TTL → source           (from fixture or prior extraction)
│   └── roundtrip.py      source → TTL → source  (same-fw or cross-fw)
├── metrics/              ← every metric exports NAME, compute, row, summarize_markdown
├── fixtures/             ← hand-authored ground-truth TTLs
```

## Pipeline matrix

| Pipeline | Input | Output | Metrics |
|---|---|---|---|
| **extraction** | `examples/<fw>/<name>/` | `output/extraction/<fw>/<name>/extracted.ttl` + report | `ttl_intrinsic`; if `ground_truth.ttl` is present: `ttl_pairwise`, `ttl_fuzzy_match` |
| **generation** | `evaluation/fixtures/<name>.ttl` _or_ an explicit `--ttl` path | `output/generation/<target>/<name>/generated/` + report | `ttl_intrinsic`, `syntax_validity`; optional: `ast_diff` (vs `--reference-source`), `ttl_pairwise` (if `--reextract`), `execution_trace` (if `--execute`) |
| **roundtrip** same-fw | `examples/<fw>/<name>/` | `output/roundtrip/<fw>/<name>/` | `ttl_pairwise`, `ttl_fuzzy_match`, `ast_diff`, `execution_trace` |
| **roundtrip** cross-fw (`--target X`) | `examples/<fw>/<name>/` | `output/roundtrip/<fw>/<name>/` | `ttl_pairwise`, `ttl_fuzzy_match`; `mapping_conformance` iff `{src, tgt} == {crewai, langgraph}` |

## Metric catalogue

| ID | What it compares | Pipelines using it |
|---|---|---|
| `ttl_intrinsic`      | counts/density of **one** TTL | extraction, generation |
| `ttl_pairwise`       | two TTLs — individual/property/triple/literal P/R/F1 | extraction (if GT), generation (if `--reextract`), roundtrip (all) |
| `ttl_fuzzy_match`    | two TTLs with fuzzy entity alignment (tolerant of URI renames) | extraction (if GT), roundtrip (all) |
| `ast_diff`           | two **source trees** in the same language — imports / classes / decorators / state fields / graph calls P/R/F1 | roundtrip same-fw, generation (with `--reference-source`) |
| `syntax_validity`    | every generated `.py` — does it `ast.parse`? do imports resolve? | generation |
| `execution_trace`    | two source trees — subprocess run, stdout overlap, exit code match | roundtrip same-fw, generation (with `--execute`) |
| `mapping_conformance`| one LangGraph tree + one CrewAI-Flow tree — canonical rule hit-rate | roundtrip cross-fw (CF↔LG only) |

Each metric module under `evaluation/metrics/` exports the same four-symbol contract:

```python
NAME: str
def compute(...) -> dict: ...
def row(result: dict) -> dict: ...                # flat fields for benchmark.csv
def summarize_markdown(result: dict) -> str: ...  # markdown block for report.md
```

Adding a new metric = adding one file that implements those four.
`evaluation/metrics/__init__.py::ALL_METRICS` auto-discovers it; `reporting.py` and `benchmark.py` render it without any other change.

## CLI

### Single example

```bash
# Extraction only
python -m evaluation.pipelines.extraction examples/crewai/email-flow -f crewai

# Generation only — from a fixture TTL (drop custom.ttl into evaluation/fixtures/)
python -m evaluation.pipelines.generation --fixture custom --target-framework crewai

# Generation only — from a prior extraction
python -m evaluation.pipelines.generation \
    --ttl output/extraction/crewai/email-flow/extracted.ttl \
    --target-framework langgraph \
    --reference-source examples/crewai/email-flow/source_files

# Roundtrip same-framework
python -m evaluation.pipelines.roundtrip examples/crewai/email-flow -f crewai

# Roundtrip cross-framework (CrewAI Flow → LangGraph)
python -m evaluation.pipelines.roundtrip examples/crewai/email-flow -f crewai -t langgraph
```

### Full benchmark

```bash
# All examples × extraction
python -m evaluation.benchmark --pipeline extraction

# All examples × same-framework roundtrip (skipping live execution)
python -m evaluation.benchmark --pipeline roundtrip --skip-execution

# Cross-framework roundtrip into LangGraph, restricted to CrewAI examples
python -m evaluation.benchmark --pipeline roundtrip \
    --frameworks crewai --target-framework langgraph

# Generate every extraction output into AutoGen and sanity-check syntax
python -m evaluation.benchmark --pipeline generation \
    --target-framework autogen --from-extraction

# Generate every fixture into CrewAI
python -m evaluation.benchmark --pipeline generation --target-framework crewai
```

Output artifacts:

```
output/<pipeline>/
├── benchmark.csv              ← one row per example, every metric's row(result) merged
├── benchmark.md               ← compact table + error section
└── <fw>/<example>/
    ├── report.json            ← full report (all metrics, structured)
    ├── report.md              ← rendered markdown summary
    └── ...                    ← pipeline-specific artefacts (ttl, generated/, ...)
```

## Authoring a fixture

To run generation experiments on hand-crafted ontologies:

1. Option A — **write Python that seeds the IR**: copy
   `evaluation/fixtures/seed_custom_system.py` as a template, construct
   your `ExtractedAgent` / `ExtractedTask` / `ExtractedFlow` objects,
   run the script. It writes `<name>.ttl` next to itself.

2. Option B — **drop a hand-authored TTL** directly into
   `evaluation/fixtures/<name>.ttl`.

Either way, `--fixture <name>` in the generation pipeline resolves the
file and feeds it to every target framework.

## Relationship to `oscin/evaluator.py`

`oscin/evaluator.py` is the **core** TTL comparator (`compute_intrinsic`,
`compute_pairwise`). `evaluation/metrics/ttl_intrinsic.py` and
`ttl_pairwise.py` are thin adapters that (a) normalise the return shape
into a plain JSON-serializable dict, and (b) implement the uniform
metric contract. **Do not duplicate** that logic; add wrappers if new
aggregations are needed.
