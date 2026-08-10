# OSCIN — Ontology-driven Source Code Interoperability

> Bidirectional transformation between agentic AI framework source code and a shared OWL ontology.

**Author:** Dani Lippmann  
**Context:** Master Thesis — *Towards Interoperability between Agentic AI Frameworks through Semantic Representation* (TU Wien, 2026)

---

## Architecture

OSCIN extends the OSCIN methodology with a three-layer pipeline:

```
                    ┌─────────────────────┐
                    │    Source Code       │
                    │  (CrewAI / AutoGen / │
                    │   LangGraph)        │
                    └────────┬────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │  Layer 1 — Parsers   │  (oscin/parsers/)    │
      │  AST + YAML          ▼                      │
      │  Framework-specific extraction              │
      └──────────────────────┬──────────────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │  Layer 2 — IR        │  (oscin/intermediate) │
      │  Shared dataclasses  ▼                      │
      │  Framework-agnostic contract                │
      └──────────────────────┬──────────────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │  Layer 3 — Populator │  (oscin/populator)   │
      │  RDFLib / OWL        ▼                      │
      │  Ontology population + validation           │
      └──────────────────────┬──────────────────────┘
                             │
                    ┌────────▼────────────┐
                    │   agentoscin.ttl    │
                    │   (OWL Ontology)    │
                    └────────┬────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │  Reverse — Reader    │  (oscin/reader)      │
      │  + Generators        ▼  (oscin/generators/) │
      │  TTL → Framework source code                │
      └─────────────────────────────────────────────┘
```

### Thesis Chapter Mapping

| Module                     | Thesis Chapter                                      |
|----------------------------|-----------------------------------------------------|
| `ontology/agentoscin.ttl`  | Ch. 5 — Semantic Representation (Ontology Design)   |
| `oscin/parsers/`           | Ch. 6 — OSCIN Phases 3 & 4 (Extraction)             |
| `oscin/intermediate.py`    | Ch. 6 — Intermediate Representation                 |
| `oscin/populator.py`       | Ch. 6 — OSCIN Phase 4 (Ontology Population)         |
| `oscin/reader.py`          | Ch. 6 — OSCIN Phase 5 (Reverse Reading)             |
| `oscin/generators/`        | Ch. 6 — OSCIN Phase 5 (Code Generation)             |
| Validation reports         | Ch. 7 — Evaluation                                  |

---

## Folder Structure

```
Extractor/
├── ontology/                # Ontology schema (OSCIN Phases 1 & 2)
│   └── agentoscin.ttl
├── oscin/                   # Python package (Phases 3–5)
│   ├── parsers/             # Framework-specific extractors
│   ├── generators/          # Framework-specific code generators
│   ├── prompts/             # LLM prompt templates
│   │   └── llm_extraction.md
│   ├── intermediate.py      # Shared dataclasses
│   ├── populator.py         # Ontology population
│   ├── reader.py            # TTL → intermediate (reverse)
│   ├── evaluator.py         # Extraction evaluation metrics
│   ├── llm_extractor.py     # LLM-based extraction baseline
│   ├── utils.py             # Shared utilities
│   └── cli.py               # CLI entry point
├── examples/                # Input test cases
│   ├── crewai/
│   ├── autogen/
│   └── langgraph/
├── output/                  # Extraction outputs (.ttl)
│   └── llm_baseline/        # LLM-based extraction outputs
├── generated/               # Generation outputs (source code)
├── .env                     # API keys (not committed)
└── docs/                    # Thesis & reference documents
```

---

## Quick Start

### Installation

```bash
pip install -e .
```

### Extract: Source Code → Ontology

```bash
# CrewAI example
oscin extract examples/crewai/email-flow/source_files \
    --framework crewai \
    --system-name EmailFlowSystem \
    --namespace "http://example.org/email_flow#" \
    --output output/crewai/email_flow_ontology.ttl

# AutoGen example
oscin extract examples/autogen/company-research/source_files \
    --framework autogen \
    --system-name CompanyResearchSystem \
    --output output/autogen/company_research.ttl
```

### Generate: Ontology → Source Code

```bash
# Same-framework round-trip
oscin generate output/crewai/email_flow_ontology.ttl \
    --target-framework crewai \
    --output-dir generated/crewai/email_flow/

# Cross-framework translation
oscin generate output/crewai/self_eval_ontology.ttl \
    --target-framework autogen \
    --output-dir generated/autogen/self_eval/
```

### LLM-Based Extraction (Baseline)

An alternative extraction method that sends the ontology schema and source code to an LLM, asking it to produce populated Turtle directly. This serves as a comparison baseline to the AST-based pipeline (inspired by the AgentO methodology).

**Setup:** Create a `.env` file in the project root with your API key:

```bash
# For OpenAI
OPENAI_API_KEY=sk-...

# For Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**Usage:**

```bash
# Using OpenAI (default: gpt-4o)
oscin extract-llm examples/crewai/email-flow/source_files \
    --namespace "http://example.org/email_flow#" \
    --output output/llm_baseline/crewai/email_flow_ontology.ttl \
    --provider openai

# Using Anthropic (default: claude-sonnet-4-20250514)
oscin extract-llm examples/crewai/email-flow/source_files \
    --namespace "http://example.org/email_flow#" \
    --output output/llm_baseline/crewai/email_flow_ontology.ttl \
    --provider anthropic

# Custom model
oscin extract-llm examples/crewai/email-flow/source_files \
    --provider openai --model gpt-4o-mini \
    --output output/llm_baseline/email_flow.ttl
```

The prompt template is in `oscin/prompts/llm_extraction.md` and can be adapted for different ontologies.

### Evaluate: Compare Extractions

Compute evaluation metrics for ontology extractions — either intrinsic metrics for a single file, or pairwise comparison (precision / recall / F1) between a reference and candidate.

```bash
# Intrinsic metrics only (single file)
oscin evaluate output/crewai/email_flow_ontology.ttl

# Pairwise comparison: AST-based (reference) vs LLM-based (candidate)
oscin evaluate output/crewai/email_flow_ontology.ttl \
    output/llm_baseline/crewai/email_flow_ontology.ttl

# JSON output (for scripts / further processing)
oscin evaluate output/crewai/email_flow_ontology.ttl \
    output/llm_baseline/crewai/email_flow_ontology.ttl --json
```

**Metrics computed:**

| Metric | Level | Description |
|--------|-------|-------------|
| Individual P/R/F1 | Type-based | Compares OWL individuals by `rdf:type`, ignoring URI naming differences |
| Property P/R/F1 | Set-based | Compares which ontology properties are used |
| Triple P/R/F1 | Exact | Compares normalized (s, p, o) triples |
| Literal overlap | Value-based | Jaccard similarity of literal string values |
| Information density | Per-file | ABox triples per individual |

---

## Supported Frameworks

| Framework | Parser | Generator | Examples |
|-----------|--------|-----------|----------|
| CrewAI    | ✅      | ✅         | 2        |
| AutoGen   | ✅      | ✅         | 3 (notebooks) |
| LangGraph | ✅      | ✅         | 1        |

---

## Dependencies

- Python ≥ 3.10
- `rdflib` ≥ 7.0
- `pyyaml` ≥ 6.0
- `nbformat` ≥ 5.0 (for notebook conversion)
- `python-dotenv` ≥ 1.0 (for `.env` API key loading)
- `anthropic` (optional, for LLM baseline with Anthropic)
- `openai` (optional, for LLM baseline with OpenAI)

---

## CrewAI Parser: How It Works

The CrewAI parser (`oscin/parsers/crewai_parser.py`) uses Python's `ast` module for static analysis (no code execution). It handles two CrewAI patterns:

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

## License

MIT — see [LICENSE](LICENSE).
