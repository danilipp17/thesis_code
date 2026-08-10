# OSCIN — Ontology-driven Source Code Interoperability

> Bidirectional transformation between agentic AI framework source code and a shared OWL ontology.

**Author:** Dani Lippmann  
**Context:** Master Thesis — *Towards Interoperability between Agentic AI Frameworks through Semantic Representation* (TU Wien, 2026)

---

## Architecture

Two transformation directions over one shared ontology, each with a
deterministic (AST/template) path and an LLM path used as a baseline:

```
                        ┌──────────────────────────────┐
                        │         Source Code          │
                        │ (CrewAI / AutoGen / LangGraph)│
                        └───────┬──────────────┬───────┘
             AST path           │              │        LLM baseline
   ┌────────────────────────────▼──┐        ┌──▼───────────────────────┐
   │ oscin/parsers/                │        │ oscin/llm_extractor.py   │
   │ AST + YAML + notebook readers │        │ schema + code → Turtle   │
   └────────────────┬──────────────┘        └──────────┬───────────────┘
                    │                                  │
   ┌────────────────▼──────────────┐                   │
   │ oscin/intermediate.py         │                   │
   │ framework-agnostic IR         │                   │
   └────────────────┬──────────────┘                   │
                    │                                  │
   ┌────────────────▼──────────────┐                   │
   │ oscin/populator.py  (RDFLib)  │                   │
   └────────────────┬──────────────┘                   │
                    │                                  │
                ┌───▼──────────────────────────────────▼───┐
                │   instance .ttl  ⊨  ontology/agentoscin.ttl │
                └───┬──────────────────────────────────┬───┘
                    │                                  │
   ┌────────────────▼──────────────┐        ┌──────────▼───────────────┐
   │ oscin/reader.py → generators/ │        │ oscin/llm_generator.py   │
   │ Jinja2 templates → source     │        │ TTL → source             │
   └────────────────┬──────────────┘        └──────────┬───────────────┘
                    └───────────────┬──────────────────┘
                                    │
                     ┌──────────────▼───────────────┐
                     │ oscin/llm_fixup.py (optional)│
                     │ repair non-running output    │
                     └──────────────────────────────┘
```

The `evaluation/` package scores all of this: extraction, generation, and
round-trip (same-framework and cross-framework).

### Thesis chapter mapping

| Module                          | Thesis chapter                                    |
|---------------------------------|---------------------------------------------------|
| `ontology/agentoscin.ttl`       | Ch. 5 — Semantic representation (ontology design) |
| `ontology/competency_queries.rq`| Ch. 5 — Competency questions                      |
| `oscin/parsers/`                | Ch. 6 — OSCIN Phases 3 & 4 (extraction)           |
| `oscin/intermediate.py`         | Ch. 6 — Intermediate representation               |
| `oscin/populator.py`            | Ch. 6 — OSCIN Phase 4 (ontology population)       |
| `oscin/reader.py`, `oscin/generators/` | Ch. 6 — OSCIN Phase 5 (reverse reading + generation) |
| `oscin/llm_*.py`                | Ch. 7 — LLM baselines and repair                  |
| `evaluation/`, `scripts/`       | Ch. 7 — Evaluation                                |

---

## Folder structure

```
thesis_code/
├── ontology/                    # Ontology schema and query assets
│   ├── agentoscin.ttl           #   the OSCIN ontology (TBox)
│   ├── agentO.ttl               #   AgentO, the related-work ontology
│   ├── competency_queries.rq    #   competency questions (SPARQL)
│   ├── combined_kg.ttl          #   merged KG over all extractions
│   ├── feature_demo.ttl         #   small worked example
│   └── catalog-v001.xml         #   Protégé catalog
├── oscin/                       # Python package (installed as `oscin`)
│   ├── parsers/                 #   crewai / autogen / langgraph + ast_utils
│   ├── generators/              #   per-framework generators + templates/*.j2
│   ├── prompts/                 #   llm_extraction.md, llm_generation.md, llm_fixup.md
│   ├── intermediate.py          #   shared IR dataclasses
│   ├── populator.py             #   IR → ontology individuals
│   ├── reader.py                #   TTL → IR (reverse direction)
│   ├── llm_extractor.py         #   LLM extraction baseline
│   ├── llm_generator.py         #   LLM generation baseline
│   ├── llm_fixup.py             #   LLM repair of generated code
│   ├── evaluator.py             #   metrics behind `oscin evaluate`
│   ├── namespaces.py, utils.py, base_parser.py
│   └── cli.py                   #   `oscin` entry point
├── evaluation/                  # Evaluation harness (not pip-installed)
│   ├── pipelines/               #   extraction / generation / roundtrip / hybrid_roundtrip
│   ├── metrics/                 #   ttl_*, ast_diff, syntax_validity, execution_trace, …
│   ├── benchmark.py             #   aggregator, driven by --pipeline
│   ├── reporting.py             #   shared report renderer
│   └── README.md                #   pipeline/metric matrix — read this first
├── gui/                         # Streamlit UI over the pipelines
├── examples/                    # Input corpora
│   ├── crewai/ autogen/ langgraph/   #   per-framework examples
│   └── parallel/                #   parallel corpus: one scenario × 3 frameworks,
│                                #   each with a hand-authored ground_truth.ttl
├── scripts/                     # One-off thesis experiment drivers
├── output/                      # Generated artifacts (TTL, source, reports)
└── .env                         # API keys (not committed)
```

`evaluation/` and `gui/` live at the project root but are **not** part of the
installed package — run them from the project root.

---

## Quick start

### Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .           # add '.[gui]' for the Streamlit UI
```

### Extract: source code → ontology

```bash
oscin extract examples/crewai/email-flow/source_files \
    --framework crewai \
    --system-name EmailFlowSystem \
    --namespace "http://example.org/email_flow#" \
    --output output/crewai/email_flow.ttl
```

`--framework` accepts `crewai`, `autogen`, `langgraph`. Add `--no-report` to
suppress the validation summary.

### Generate: ontology → source code

```bash
# Same-framework round-trip
oscin generate output/crewai/email_flow.ttl \
    --target-framework crewai \
    --output-dir output/generated/crewai/email_flow/

# Cross-framework translation
oscin generate output/crewai/email_flow.ttl \
    --target-framework autogen \
    --output-dir output/generated/autogen/email_flow/
```

### LLM baselines

Both directions have an LLM counterpart used as a comparison baseline
(inspired by the AgentO methodology). Put your key in a `.env` at the project
root (`OPENAI_API_KEY=…` and/or `ANTHROPIC_API_KEY=…`); it is loaded from the
working directory and from `~/.env`.

```bash
# Extraction baseline — default provider is anthropic
oscin extract-llm examples/crewai/email-flow/source_files \
    --namespace "http://example.org/email_flow#" \
    --output output/llm_baseline/crewai/email_flow.ttl \
    --provider openai --model gpt-4o-mini

# Generation baseline
oscin generate-llm output/crewai/email_flow.ttl \
    --target-framework crewai \
    --output-dir output/generated_llm/crewai/email_flow/ \
    --provider anthropic
```

Prompt templates live in `oscin/prompts/` and can be adapted for other
ontologies.

### Evaluate a pair of TTLs

`oscin evaluate` is the quick, single-shot comparison — one file for intrinsic
metrics, two for precision/recall/F1.

```bash
oscin evaluate output/crewai/email_flow.ttl                        # intrinsic only
oscin evaluate reference.ttl candidate.ttl                         # pairwise
oscin evaluate reference.ttl candidate.ttl --json                  # machine-readable
```

| Metric | Level | Description |
|--------|-------|-------------|
| Individual P/R/F1 | Type-based | Compares OWL individuals by `rdf:type`, ignoring URI naming differences |
| Property P/R/F1 | Set-based | Compares which ontology properties are used |
| Triple P/R/F1 | Exact | Compares normalized (s, p, o) triples |
| Literal overlap | Value-based | Jaccard similarity of literal string values |
| Information density | Per-file | ABox triples per individual |

### Evaluate a whole pipeline

The full harness lives in `evaluation/` and is driven by `--pipeline`:

```bash
python -m evaluation.benchmark --pipeline extraction --frameworks crewai langgraph
python -m evaluation.benchmark --pipeline generation --target-framework crewai --execute --reextract
python -m evaluation.benchmark --pipeline roundtrip  --frameworks crewai --target-framework langgraph
```

Useful flags: `--only crewai/email-flow` to restrict to single examples,
`--from-extraction` to feed generation from prior extractions instead of
fixtures, `--out-root` to redirect artifacts.

See [evaluation/README.md](evaluation/README.md) for the pipeline × metric
matrix and the contract every metric module implements.

### GUI

```bash
streamlit run gui/app.py     # requires the [gui] extra
```

---

## Supported frameworks

| Framework | Parser | Generator | Examples |
|-----------|--------|-----------|----------|
| CrewAI    | ✅ | ✅ | 11 |
| AutoGen   | ✅ | ✅ | 8 (incl. notebooks) |
| LangGraph | ✅ | ✅ | 12 |

Plus `examples/parallel/` — 6 scenario families implemented in all three
frameworks, each variant shipping a hand-authored `ground_truth.ttl`. See
[examples/parallel/README.md](examples/parallel/README.md).

---

## Dependencies

Declared in `pyproject.toml`: Python ≥ 3.10, `rdflib` ≥ 7.0, `pyyaml` ≥ 6.0,
`nbformat` ≥ 5.0; `streamlit` ≥ 1.32 under the `gui` extra.

Also imported at runtime but **not currently declared**: `jinja2` (required by
`oscin/generators/`), `python-dotenv` (LLM paths), and `openai` / `anthropic`
(whichever provider you use for the LLM baselines). Install them alongside the
package until they are added to `pyproject.toml`.

---

## CrewAI parser: how it works

The CrewAI parser (`oscin/parsers/crewai_parser.py`) uses Python's `ast` module
for static analysis (no code execution). It handles two CrewAI patterns:

1. **@CrewBase pattern** — YAML-configured crews:
   - Reads `agents.yaml` and `tasks.yaml` from the `config/` directory (resolved via `@CrewBase` class annotations)
   - Extracts agent metadata (role, goal, backstory, tools, LLM) and task metadata (description, expected_output, agent assignment)
   - Resolves `llm=self.llm` references to class-level LLM assignments (e.g., `ChatOpenAI(model="gpt-4o")`)
   - Resolves local variable tool references (e.g., `search_tool = SerperDevTool()` → tool name "SerperDevTool")

2. **Flow pattern** — `@start`, `@listen`, `@router` decorators:
   - Extracts workflow steps and their sequencing from decorator arguments
   - Maps steps to tasks via `hasAssociatedTask` when a crew kickoff is detected

**Tool extraction** supports:
- `BaseTool` subclasses with `name`/`description` fields
- `@tool("name")` decorated functions
- External/imported tools are created as stub individuals with `hasReference "external:ToolName"`

**Requirements for source code to parse correctly:**
- YAML config files must match the agent/task keys referenced in Python decorators
- Tools must be either defined locally (BaseTool subclass or @tool decorator) or imported (created as external stubs)
- LLM assignments should use `ChatOpenAI(model="...")` or similar patterns with string literal model names

---

## License

MIT — see [LICENSE](LICENSE).
