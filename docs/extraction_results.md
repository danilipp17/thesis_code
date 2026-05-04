# Extraction Experiment Results

## Overview

The OSCIN extraction pipeline was executed on **20 benchmark examples** across three agentic AI frameworks: **CrewAI** (7 examples), **AutoGen** (7 examples), and **LangGraph** (6 examples). Each example is a real multi-agent system source project that was automatically transformed into an agentoscin OWL ABox (RDF/Turtle file). The metrics below characterise the resulting knowledge graphs.

---

## Metric Legend

| Metric | Symbol | Definition |
|--------|--------|------------|
| **Total Triples** | `total_triples` | Total number of RDF triples in the output `.ttl` file, including both TBox (ontology schema imports) and ABox (instance data). |
| **ABox Triples** | `abox_triples` | Number of instance-level (ABox) triples only — excludes ontology-level class/property declarations and OWL axioms. These are the triples that describe the extracted system. |
| **Total Individuals** | `total_individuals` | Count of distinct named OWL individuals in the ABox (e.g., each agent, task, tool, workflow step is one individual). |
| **Properties Used** | `property_count` | Number of *distinct* agentoscin ontology properties exercised in the ABox triples (e.g., `agentRole`, `hasAgentGoal`, `nextStep`). Higher values indicate richer semantic annotation. |
| **Information Density** | `information_density` | Ratio: `abox_triples / total_individuals`. Measures how richly described each individual is on average. Higher = more properties per entity. |
| **Literals Count** | `literals_count` | Number of ABox triples whose object is a literal value (string, boolean, integer). These carry textual content such as prompts, descriptions, schema definitions. |
| **Object Links Count** | `object_links_count` | Number of ABox triples whose object is another named individual (URI). These represent structural relationships (e.g., agent→tool, step→next_step, team→agent). |

### Derived Ratios (computed below per framework)

| Ratio | Definition |
|-------|------------|
| **Link Ratio** | `object_links / abox_triples` — proportion of structural (relational) triples vs total instance data. |
| **TBox Overhead** | `(total_triples - abox_triples) / total_triples` — fraction of triples that are ontology schema (imported TBox). Constant base ~498 triples. |

---

## Per-Example Detailed Results

### CrewAI Examples (7)

| # | Example | Total Triples | ABox Triples | Individuals | Properties | Density | Literals | Object Links |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | academic-research-flow | 688 | 190 | 44 | 53 | 4.32 | 83 | 102 |
| 2 | code-review | 694 | 196 | 41 | 44 | 4.78 | 88 | 103 |
| 3 | comprehensive | 672 | 174 | 40 | 55 | 4.35 | 75 | 94 |
| 4 | content-pipeline | 673 | 175 | 35 | 42 | 5.00 | 79 | 91 |
| 5 | email-flow | 685 | 187 | 38 | 44 | 4.92 | 84 | 98 |
| 6 | self-eval-loop-flow | 649 | 151 | 34 | 40 | 4.44 | 65 | 81 |
| 7 | tech-blog | 636 | 138 | 26 | 34 | 5.31 | 62 | 71 |

**CrewAI Individual Breakdown:**

| Example | Agents | Tasks | Tools | Teams | Orchestrations | Flow Steps* | Schemas | Prompts | Goals | Other |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| academic-research-flow | 3 | 2 | 1 | 1 | 1 | 12 | 3 | 4 | 2 | 15 |
| code-review | 3 | 3 | 1 | 1 | 1 | 13 | 2 | 6 | 3 | 8 |
| comprehensive | 2 | 2 | 2 | 1 | 1 | 10 | 2 | 4 | 2 | 14 |
| content-pipeline | 3 | 3 | 2 | 1 | 1 | 7 | 1 | 6 | 3 | 8 |
| email-flow | 3 | 3 | 4 | 1 | 1 | 7 | 1 | 6 | 3 | 9 |
| self-eval-loop-flow | 2 | 2 | 1 | 2 | 1 | 12 | 2 | 4 | 2 | 6 |
| tech-blog | 3 | 3 | 0 | 1 | 0 | 3 | 0 | 6 | 3 | 7 |

*Flow Steps = StartStep + WorkflowStep + ConditionalStep + EndStep combined.

---

### AutoGen Examples (7)

| # | Example | Total Triples | ABox Triples | Individuals | Properties | Density | Literals | Object Links |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | code-review | 598 | 100 | 20 | 30 | 5.00 | 43 | 52 |
| 2 | company-research | 621 | 123 | 25 | 30 | 4.92 | 58 | 60 |
| 3 | content-pipeline | 604 | 106 | 21 | 30 | 5.05 | 47 | 54 |
| 4 | data-analysis-0.4 | 603 | 105 | 22 | 30 | 4.77 | 46 | 54 |
| 5 | literature-review | 622 | 124 | 25 | 30 | 4.96 | 59 | 60 |
| 6 | tech-blog | 591 | 93 | 19 | 27 | 4.89 | 39 | 49 |
| 7 | travel-planning | 626 | 128 | 26 | 27 | 4.92 | 58 | 65 |

**AutoGen Individual Breakdown:**

| Example | Agents | Tasks | Tools | Teams | Orchestrations | Flow Steps* | Termination | Prompts | Goals | LMs |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| code-review | 3 | 1 | 1 | 1 | 1 | 2 | 1 (TurnLimit) | 4 | 3 | 1 |
| company-research | 3 | 1 | 3 | 1 | 1 | 2 | 1 (TurnLimit) | 7 | 3 | 1 |
| content-pipeline | 3 | 1 | 2 | 1 | 1 | 2 | 1 (TurnLimit) | 4 | 3 | 1 |
| data-analysis-0.4 | 3 | 1 | 2 | 1 | 1 | 2 | 1 (TurnLimit) | 4 | 3 | 2 |
| literature-review | 3 | 1 | 3 | 1 | 1 | 2 | 1 (EventBased) | 7 | 3 | 1 |
| tech-blog | 3 | 1 | 0 | 1 | 1 | 2 | 1 (TurnLimit) | 4 | 3 | 1 |
| travel-planning | 4 | 1 | 0 | 1 | 1 | 2 | 1 (EventBased) | 9 | 4 | 1 |

*Flow Steps for AutoGen = StartStep + WorkflowStep (always 1+1=2 because AutoGen has a single orchestration entry point).

---

### LangGraph Examples (6)

| # | Example | Total Triples | ABox Triples | Individuals | Properties | Density | Literals | Object Links |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ReAct | 584 | 86 | 18 | 35 | 4.78 | 36 | 45 |
| 2 | drafter | 576 | 78 | 17 | 33 | 4.59 | 30 | 43 |
| 3 | memoryagent | 567 | 69 | 17 | 28 | 4.06 | 21 | 43 |
| 4 | ragagent | 600 | 102 | 22 | 35 | 4.64 | 40 | 57 |
| 5 | research-assistant | 609 | 111 | 24 | 36 | 4.63 | 46 | 60 |
| 6 | tech-blog | 631 | 133 | 28 | 31 | 4.75 | 49 | 79 |

**LangGraph Individual Breakdown:**

| Example | Agents | Tasks | Tools | Teams | Orchestrations | Flow Steps* | Termination | Schemas | Prompts | Goals |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ReAct | 1 | 1 | 3 | 1 | 1 | 4 | 1 (Routing) | 1 | 2 | 0 |
| drafter | 1 | 1 | 2 | 1 | 1 | 4 | 1 (Routing) | 1 | 2 | 0 |
| memoryagent | 1 | 1 | 0 | 1 | 1 | 4 | 1 (Routing) | 1 | 2 | 1 |
| ragagent | 2 | 2 | 1 | 1 | 1 | 4 | 1 (Routing) | 1 | 4 | 2 |
| research-assistant | 2 | 2 | 2 | 1 | 1 | 5 | 1 (Routing) | 1 | 4 | 2 |
| tech-blog | 3 | 3 | 0 | 1 | 1 | 8 | 1 (Routing) | 1 | 6 | 0 |

*Flow Steps = StartStep + WorkflowStep + ConditionalStep + EndStep combined.

---

## Aggregate Statistics by Framework

| Metric | CrewAI (n=7) | AutoGen (n=7) | LangGraph (n=6) | All (n=20) |
|--------|:---:|:---:|:---:|:---:|
| **Mean Total Triples** | 671.0 | 609.3 | 594.5 | 626.5 |
| **Mean ABox Triples** | 173.0 | 111.3 | 96.5 | 128.4 |
| **Mean Individuals** | 36.9 | 22.6 | 21.0 | 27.1 |
| **Mean Properties Used** | 44.6 | 29.1 | 33.0 | 35.7 |
| **Mean Density** | 4.73 | 4.93 | 4.57 | 4.75 |
| **Mean Literals** | 76.6 | 50.0 | 37.0 | 55.4 |
| **Mean Object Links** | 91.4 | 56.3 | 54.5 | 68.0 |
| **Mean Link Ratio** | 0.53 | 0.51 | 0.57 | 0.53 |
| **Min Individuals** | 26 | 19 | 17 | 17 |
| **Max Individuals** | 44 | 26 | 28 | 44 |
| **Min Properties** | 34 | 27 | 28 | 27 |
| **Max Properties** | 55 | 30 | 36 | 55 |

---

## Ontology Property Coverage per Framework

The following shows how many of the agentoscin ontology's data/object properties are exercised by each framework's extracted outputs.

| Framework | Properties Exercised | Notable Exclusive Properties |
|-----------|:---:|------|
| CrewAI | 34–55 (mean 44.6) | `hasGuardrail`, `hasKnowledge`, `hasTeamMemoryBinding`, `hasMemoryBinding`, `bindsMemory`, `hasOutputSchema`, `taskToolUsage`, `configKey/configValue` |
| AutoGen | 27–30 (mean 29.1) | `hasMaxTurns`, `hasTerminationCondition`, `hasTriggerExpression` |
| LangGraph | 28–36 (mean 33.0) | `hasAssociatedAgent`, `hasEdgeMapping`, `hasRoutingLogic`, `nextStep` (back-edges) |

**Observations:**
- CrewAI exercises the broadest property vocabulary because it exposes the most declarative configuration (memory, guardrails, output schemas, knowledge bases, delegation strategies).
- AutoGen has a remarkably consistent property count (27–30) because the parser uniformly synthesises the same structural pattern for all RoundRobin/SelectorBased teams.
- LangGraph is the only framework that produces `hasAssociatedAgent` (agent↔workflow-step binding) and `hasEdgeMapping` (conditional routing tables).

---

## Individual Type Distribution (Totals across all examples)

| OWL Class | CrewAI | AutoGen | LangGraph | Total |
|-----------|:---:|:---:|:---:|:---:|
| LLMAgent | 19 | 22 | 10 | 51 |
| Task | 18 | 7 | 10 | 35 |
| Tool | 11 | 11 | 8 | 30 |
| Team | 8 | 7 | 6 | 21 |
| Orchestration | 6 | 7 | 6 | 19 |
| Prompt | 36 | 39 | 20 | 95 |
| Goal | 18 | 22 | 5 | 45 |
| WorkflowStep | 26 | 7 | 13 | 46 |
| StartStep | 14 | 7 | 8 | 29 |
| EndStep | 20 | 0 | 5 | 25 |
| ConditionalStep | 4 | 0 | 3 | 7 |
| Schema | 11 | 0 | 6 | 17 |
| LanguageModel | 6 | 8 | 6 | 20 |
| Config | 27 | 0 | 0 | 27 |
| WorkflowPattern | 14 | 7 | 8 | 29 |
| Memory | 4 | 0 | 0 | 4 |
| MemoryBinding | 4 | 0 | 0 | 4 |
| TurnLimitTermination | 0 | 5 | 0 | 5 |
| EventBasedTermination | 0 | 2 | 0 | 2 |
| RoutingTermination | 0 | 0 | 6 | 6 |
| HumanCheckpoint | 2 | 0 | 0 | 2 |
| Guardrail | 1 | 0 | 0 | 1 |
| KnowledgeBase | 1 | 0 | 0 | 1 |
| Unspecified | 1 | 0 | 0 | 1 |
| AgenticSystem | 7 | 7 | 6 | 20 |

---

## Structural Metrics: TBox vs ABox

Every extracted TTL file imports the agentoscin ontology schema, which contributes a constant base of approximately **498 TBox triples**. The variable portion is the ABox (instance data).

| Framework | Mean TBox Base | Mean ABox | ABox % of Total |
|-----------|:---:|:---:|:---:|
| CrewAI | ~498 | 173.0 | 25.8% |
| AutoGen | ~498 | 111.3 | 18.3% |
| LangGraph | ~498 | 96.5 | 16.2% |

---

## Information Density Analysis

Information density = ABox triples per individual. It measures how richly annotated each entity is.

| Range | Interpretation | Examples |
|-------|---------------|----------|
| < 4.0 | Sparse — entities with few properties filled | memoryagent (4.06) |
| 4.0–4.5 | Moderate | academic-research-flow (4.32), comprehensive (4.35) |
| 4.5–5.0 | Typical | Most examples cluster here (mean 4.75) |
| > 5.0 | Dense — entities richly annotated | content-pipeline (5.05), tech-blog-crewai (5.31) |

**Why do densities vary?**
- Higher density: agents have many properties filled (tools, memory, reasoning, delegation strategy, config).
- Lower density: agents defined minimally (just role + system message) or many "structural" individuals (empty flow steps) inflate the denominator.

---

## Consistency and Structural Invariants

The extraction pipeline enforces the following structural invariants visible in the data:

| Invariant | Verified | Evidence |
|-----------|:---:|---------|
| Every extracted file contains exactly 1 `AgenticSystem` | ✓ | All 20 examples: AgenticSystem = 1 |
| Every `AgenticSystem` contains ≥1 `Team` | ✓ | All 20 examples: Team ≥ 1 |
| Every `Team` has ≥1 `LLMAgent` member | ✓ | All 20 examples: LLMAgent ≥ 1 |
| Every `LLMAgent` has exactly 1 `Prompt` | ✓* | Prompt count matches/exceeds agent count in all examples |
| Every `Orchestration` has ≥1 `WorkflowStep` | ✓ | All examples with Orchestration have flow steps |
| AutoGen always produces exactly 1 termination condition | ✓ | All 7 AutoGen examples: exactly 1 termination individual |
| LangGraph always produces `RoutingTermination` | ✓ | All 6 LangGraph examples: RoutingTermination = 1 |

*Prompt individuals may exceed agents because Tasks also produce `TaskPrompt` individuals.

---

## Discussion of Results

### Key Findings

1. **Systematic extraction succeeds across all 20 examples.** Every source project produced a valid, parseable TTL file with non-trivial ABox content (minimum 69 triples, 17 individuals).

2. **Framework complexity correlates with ABox size.** CrewAI examples produce the largest knowledge graphs (mean 173 ABox triples, 36.9 individuals) because CrewAI exposes the most declarative configuration. AutoGen's API is more compact, yielding smaller but denser graphs.

3. **Property coverage is framework-characteristic.** AutoGen examples converge to a consistent 27–30 property vocabulary. CrewAI varies widely (34–55) depending on which optional features (memory, guardrails, knowledge) each example uses. LangGraph sits in between (28–36) with its graph-topology properties.

4. **Information density is remarkably stable.** Across all 20 examples, density ranges from 4.06 to 5.31 (mean 4.75, σ ≈ 0.30). This stability reflects the ontology's design: each entity type has a consistent set of mandatory properties, and the pipeline fills them uniformly.

5. **Structural relationships (object links) account for ~53% of ABox triples.** The extraction captures not just textual content but the actual architectural topology — agent-to-team membership, task-to-agent assignment, workflow step sequencing, and tool bindings.

6. **The ontology's framework-agnostic design is validated.** All three frameworks map into the same 20+ OWL classes and 27–55 properties, demonstrating that agentoscin successfully abstracts over framework-specific APIs while preserving semantic content.

### Limitations Visible in the Data

- **No pairwise (P/R/F1) metrics available.** Ground-truth TTL files do not exist for these examples, so the evaluation is limited to intrinsic metrics. The benchmark CSV columns `triple_f1`, `property_f1`, `individual_f1`, and `fuzzy_avg_score` all show "—".
- **AutoGen Goal synthesis.** The parser splits `system_message` into Goal + Prompt individuals. The Goal's content is sometimes semantically imprecise (first sentence of a persona description rather than an actual objective).
- **Conditional edge resolution (LangGraph).** Router labels (e.g., "continue", "end") are looked up directly in the step label map rather than resolved through `edge_mapping` → some conditional forward edges are missing from the topology.
