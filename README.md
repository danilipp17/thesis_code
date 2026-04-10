# OSCIN — Ontology-driven Source Code Interoperability

A multi-framework extraction pipeline that statically analyses agentic AI source code and populates an OWL ontology instance. Part of the master thesis *"Towards Interoperability between Agentic AI Frameworks through Semantic Representation"*.

## Supported Frameworks

| Framework | Parser | Status |
|-----------|--------|--------|
| **CrewAI** | `CrewAIParser` | ✅ Fully implemented & tested |
| **AutoGen** | `AutoGenParser` | 🔧 Pattern detection ready, awaiting example projects |
| **LangGraph** | `LangGraphParser` | 🔧 Pattern detection ready, awaiting example projects |

## Architecture

The pipeline follows a three-layer architecture that separates syntactic parsing from semantic population:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — Framework-Specific Parsers                   │
│  (AST + YAML → Intermediate Representation)             │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ CrewAIParser  │ │ AutoGenParser│ │ LangGraphParser  │ │
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘ │
└─────────┼────────────────┼──────────────────┼───────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2 — Shared Intermediate Representation           │
│                                                         │
│  ExtractedAgent · ExtractedTask · ExtractedTool          │
│  ExtractedTeam  · ExtractedFlow · ExtractedFlowStep      │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3 — Ontology Population (RDFLib)                 │
│                                                         │
│  OntologyPopulator  →  .ttl (Turtle) output             │
└─────────────────────────────────────────────────────────┘
```

Each framework parser reads source code using Python's `ast` module, extracts agentic constructs, and maps them into framework-agnostic dataclasses. The shared `OntologyPopulator` then converts these into RDF triples using the [AGENTO](http://w3id.org/2025/agento/ontology#) vocabulary.

## Project Structure

```
Extractor/
├── oscin/                              # Extraction pipeline package
│   ├── __init__.py
│   ├── namespaces.py                   # AGENTO namespace + instance NS factory
│   ├── intermediate.py                 # Shared dataclasses (the contract)
│   ├── base_parser.py                  # Abstract base class for parsers
│   ├── populator.py                    # Shared OntologyPopulator
│   ├── cli.py                          # CLI entry point
│   └── parsers/
│       ├── __init__.py
│       ├── crewai_parser.py            # CrewAI: @CrewBase, @agent, @task, Flow
│       ├── autogen_parser.py           # AutoGen: AssistantAgent, GroupChat, etc.
│       └── langgraph_parser.py         # LangGraph: StateGraph, add_node, etc.
│
├── examples/                           # Source code inputs (by framework)
│   ├── crewai/
│   │   ├── email-flow/source_files/
│   │   └── self-eval-loop-flow/source_files/
│   ├── autogen/
│   └── langgraph/
│
├── output/                             # Generated ontology files (by framework)
│   ├── crewai/
│   ├── autogen/
│   └── langgraph/
│
└── README.md
```

## Prerequisites

- Python 3.10+
- Dependencies: `rdflib`, `pyyaml`

```bash
pip install rdflib pyyaml
```

## Usage

### CLI

```bash
python -m oscin.cli <source_dir> \
    --framework <crewai|autogen|langgraph> \
    --system-name <name> \
    [--namespace <uri>] \
    [--output <file>] \
    [--no-report]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `source_dir` | ✅ | Path to the source files directory |
| `--framework`, `-f` | ✅ | Framework: `crewai`, `autogen`, or `langgraph` |
| `--system-name`, `-s` | ✅ | Name for the `AgenticSystem` individual |
| `--namespace`, `-n` | | Instance namespace URI (default: `http://example.org/instance#`) |
| `--output`, `-o` | | Output `.ttl` file path (default: `output_ontology.ttl`) |
| `--no-report` | | Suppress the validation report |

### Examples

**CrewAI — Email Auto-Responder Flow:**
```bash
python -m oscin.cli examples/crewai/email-flow/source_files \
    --framework crewai \
    --system-name EmailFlowSystem \
    --namespace "http://example.org/email_flow#" \
    --output output/crewai/email_flow_ontology.ttl
```

**CrewAI — Self-Evaluation Loop:**
```bash
python -m oscin.cli examples/crewai/self-eval-loop-flow/source_files \
    --framework crewai \
    --system-name SelfEvaluationLoopSystem \
    --namespace "http://example.org/self_evaluation_loop_flow#" \
    --output output/crewai/self_eval_ontology.ttl
```

**AutoGen (once example files are added):**
```bash
python -m oscin.cli examples/autogen/my-project/source_files \
    --framework autogen \
    --system-name MyAutoGenSystem \
    --output output/autogen/my_ontology.ttl
```

**LangGraph (once example files are added):**
```bash
python -m oscin.cli examples/langgraph/my-project/source_files \
    --framework langgraph \
    --system-name MyLangGraphSystem \
    --output output/langgraph/my_ontology.ttl
```

## How It Works

### What Each Parser Detects

#### CrewAI Parser
| Source Construct | → Intermediate |
|---|---|
| `@CrewBase` class | `ExtractedTeam` |
| `@agent` method + YAML config | `ExtractedAgent` |
| `@task` method + YAML config | `ExtractedTask` |
| `BaseTool` subclass | `ExtractedTool` |
| `Flow` subclass with `@start` / `@listen` / `@router` | `ExtractedFlow` + `ExtractedFlowStep` |

#### AutoGen Parser
| Source Construct | → Intermediate |
|---|---|
| `AssistantAgent(name=..., system_message=...)` | `ExtractedAgent` |
| `UserProxyAgent(name=..., ...)` | `ExtractedAgent` |
| `GroupChat(agents=[...])` | `ExtractedTeam` |
| `GroupChatManager(...)` | Hierarchical coordination pattern |
| `register_function(...)` / `@tool` | `ExtractedTool` |
| `agent.initiate_chat(...)` | `ExtractedFlowStep` |

#### LangGraph Parser
| Source Construct | → Intermediate |
|---|---|
| `StateGraph(State)` | `ExtractedFlow` |
| `graph.add_node("name", func)` | `ExtractedFlowStep` |
| `graph.add_edge("a", "b")` | Step connectivity |
| `graph.add_conditional_edges(...)` | `ExtractedFlowStep` (router) |
| `ToolNode([tools])` / `@tool` | `ExtractedTool` |
| Node functions with LLM calls | `ExtractedAgent` |

### Ontology Output

The pipeline produces Turtle (`.ttl`) files using the AGENTO vocabulary. Key ontology classes populated:

- `agento:AgenticSystem` — top-level system container
- `agento:LLMAgent` — individual agents with roles, goals, prompts
- `agento:Task` — tasks with descriptions, expected outputs, agent assignments
- `agento:Team` — groups of agents with coordination patterns
- `agento:Tool` — tools with input schemas and implementation references
- `agento:Orchestration` — flow-level workflow with steps and routing

## Adding a New Framework

1. Create a new parser in `oscin/parsers/` inheriting from `BaseSourceParser`
2. Implement `parse_all()` to populate the intermediate-representation dictionaries
3. Implement `framework_name()` to return the framework label
4. Register the parser in `oscin/cli.py` → `PARSERS` dict
5. Add an `examples/<framework>/` directory for test source files

## Author

**Dani Lippmann** — Master Thesis, April 2026
