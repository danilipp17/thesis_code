---
name: Evaluation subset (6 systems)
description: Six systems chosen for the redesigned evaluation, with selection rationale per framework
---

# Evaluation subset (6 systems, 2 per framework)

The six systems span the architectural patterns each framework is used for in
practice — single-agent reasoning, multi-agent coordination, control-flow
orchestration, and human-in-the-loop. Each pair is designed so that one
system exercises *core* extraction features (agent / tool / prompt / config)
while the other forces *non-trivial* features (HITL, reasoning loops, routing,
multi-step coordination).

| # | Framework  | System                  | Core constructs exercised                                                                  | Why included                                                                 |
|---|------------|--------------------------|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| 1 | CrewAI     | `email-flow`             | `@Flow` with `@start`/`@listen`/`@router`, multiple Crews, conditional routing              | Control-flow-heavy; tests workflow-step + transition extraction              |
| 2 | CrewAI     | `academic-research-flow` | Flow + nested Crew(s), YAML-configured agents/tasks, tool registry                          | Tests YAML→A-Box mapping and multi-crew composition                          |
| 3 | LangGraph  | `ReAct`                  | `create_react_agent`, single tool-using agent                                               | Tests reasoning pattern detection (ReAct)                                    |
| 4 | LangGraph  | `research-assistant`     | `StateGraph`, multi-node graph, conditional routing, two distinct agents + tools             | Tests multi-agent graph + conditional edges (no HITL)                        |
| 5 | AutoGen    | `code-review`            | `AssistantAgent` + `UserProxyAgent`, tool registration                                      | Tests classic 2-agent dialogue + tool wiring                                 |
| 6 | AutoGen    | `content-pipeline`       | Multi-agent group-chat / round-robin coordination                                           | Tests coordination pattern + multi-agent team extraction                     |

## Coverage matrix

| Feature                       | 1 | 2 | 3 | 4 | 5 | 6 |
|-------------------------------|---|---|---|---|---|---|
| Agents (≥1)                   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Multiple agents (team)        | ✓ | ✓ |   | ✓ | ✓ | ✓ |
| Tools                         | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| YAML configs                  | ✓ | ✓ |   |   |   |   |
| Workflow steps / Tasks        | ✓ | ✓ |   | ✓ |   | ✓ |
| Conditional routing           | ✓ |   |   | ✓ |   |   |
| Human-in-the-loop             |   |   |   |   | ✓ |   |
| Reasoning pattern (ReAct)     |   |   | ✓ |   |   |   |
| Coordination pattern          | ✓ | ✓ |   | ✓ | ✓ | ✓ |
| Memory / state                |   |   | ✓ | ✓ |   |   |

The matrix shows every ontology-relevant feature class is covered by at least
two systems — except HITL and ReAct, each of which appears in only one
system in the subset. Per-feature precision/recall on those two features is
therefore presence/absence rather than a population estimate, and the thesis
flags it as such.
