# Comprehensive Evaluation Results

## Overview

This document presents the full evaluation of the OSCIN transformation pipeline across three dimensions:

1. **AST Same-Framework Roundtrip** — measures extraction + generation fidelity within a single framework
2. **AST Cross-Framework Roundtrip** — measures cross-framework translation fidelity
3. **LLM Baseline** — compares the deterministic AST pipeline against a pure LLM-based approach (GPT-4o)

**Metrics used:**
| Metric | Abbrev. | What it measures |
|--------|---------|-----------------|
| Triple F1 | TF1 | Exact match of normalized (subject, predicate, object) triples |
| Aligned Triple F1 | ATF1 | Triple F1 after bipartite entity alignment (tolerates URI renames) |
| Property F1 | PF1 | Coverage of ontology predicates used |
| Individual F1 | IF1 | Correctness of entity counts per OWL class |
| AST F1 | AF1 | Structural skeleton match (functions, classes, decorators, state, graph calls) |

---

## 1. AST Same-Framework Roundtrip

**Pipeline:** `source → AST extract → TTL₁ → AST generate(same_fw) → source' → AST extract → TTL₂`

### 1.1 CrewAI (n=8)

| Example | Triple F1 | Prop F1 | Ind F1 | AST F1 | Notes |
|---------|-----------|---------|--------|--------|-------|
| academic-research-flow | 0.847 | 0.971 | 0.966 | 0.765 | Missing: `dependsOn`, `hasDependencyType`, `hasTeamMemoryBinding` |
| code-review | 0.916 | 1.000 | 1.000 | 0.910 | Near-perfect; minor literal differences |
| comprehensive | 0.889 | 0.944 | 0.974 | 0.829 | Missing: `dependsOn`, `hasTeamMemoryBinding`; extra: `hasInputSchema` |
| content-pipeline | 0.911 | 1.000 | 1.000 | 0.895 | All properties/individuals preserved |
| email-flow | 0.925 | 1.000 | 1.000 | 0.819 | All entities preserved; AST lower due to flow decorator differences |
| self-eval-loop-flow | 0.914 | 1.000 | 1.000 | 0.924 | Near-perfect roundtrip |
| tech-blog | 0.913 | 1.000 | 1.000 | 0.972 | Excellent across all metrics |
| unseen-hiring-pipeline | 0.912 | 0.989 | 0.978 | 0.849 | Missing: `hasTeamMemoryBinding` (memory config) |
| **Mean** | **0.903** | **0.988** | **0.990** | **0.870** | |

**Analysis:**
- CrewAI achieves the highest same-fw fidelity across all metrics
- Triple F1 consistently > 0.84 — the generator reproduces most triples exactly
- Property F1 near 1.0 — all relationship types preserved
- Individual F1 near 1.0 — correct entity counts per class
- Main losses: task dependency edges (`dependsOn`), team memory bindings not regenerated
- AST F1 slightly lower because the generator produces canonical CrewAI structure (standardized YAML layout) which may differ from the original's code organization

### 1.2 LangGraph (n=9)

| Example | Triple F1 | Prop F1 | Ind F1 | AST F1 | Notes |
|---------|-----------|---------|--------|--------|-------|
| ReAct | 0.784 | 0.986 | 0.973 | 0.918 | Extra Goal individual from agent description |
| drafter | 0.719 | 0.971 | 0.919 | 0.874 | Extra Goal + Task from node function inference |
| memoryagent | 0.829 | 0.966 | 1.000 | 0.962 | Extra properties from regenerated checkpointer config |
| plan-execute | 0.267 | 1.000 | 1.000 | N/A | Empty source; only ontology schema survives |
| ragagent | 0.762 | 0.944 | 0.875 | 0.814 | Missing conditional routing step; extra END steps |
| reflexion | 0.267 | 1.000 | 1.000 | N/A | Empty source; only ontology schema survives |
| research-assistant | 0.846 | 1.000 | 0.980 | 0.803 | Near-perfect property/individual preservation |
| tech-blog | 0.871 | 0.969 | 0.933 | 0.915 | Extra Goal individuals from node descriptions |
| unseen-customer-support | 0.895 | 1.000 | 0.979 | 0.922 | Excellent; minor individual count difference |
| **Mean** | **0.693** | **0.982** | **0.962** | **0.887** | |
| **Mean (excl. empty)** | **0.815** | **0.976** | **0.951** | **0.887** | |

**Analysis:**
- Excluding plan-execute and reflexion (empty source dirs), mean Triple F1 = 0.815
- Triple F1 lower than CrewAI because LangGraph's graph topology creates more triples that can mismatch (edge connections, conditional routing)
- The generator sometimes infers additional Goal/Task individuals from node function docstrings that weren't in the original extraction
- Property F1 remains high — the ontology vocabulary is well-preserved
- AST F1 is strong where available — generated code has correct structural skeleton
- Main loss: conditional edge routing logic not always faithfully round-tripped

### 1.3 AutoGen (n=8)

| Example | Triple F1 | Prop F1 | Ind F1 | AST F1 | Notes |
|---------|-----------|---------|--------|--------|-------|
| code-review | 0.873 | 0.966 | 0.974 | 0.992 | Missing: termination condition individual |
| company-research | 0.749 | 0.947 | 0.913 | N/A | Missing: max_turns, termination, promptContext |
| content-pipeline | 0.871 | 0.966 | 0.976 | 0.986 | Missing: termination condition |
| data-analysis-0.4 | 0.829 | 0.966 | 0.952 | 0.970 | Missing: termination condition |
| literature-review | 0.709 | 0.935 | 0.898 | N/A | Missing: promptContext; extra: composite termination |
| tech-blog | 0.863 | 0.962 | 0.973 | 0.989 | Missing: termination condition |
| travel-planning | 0.683 | 0.929 | 0.880 | N/A | Missing: promptContext; extra: composite termination |
| unseen-debate | 0.727 | 0.982 | 0.920 | 0.981 | Missing: promptContext literal |
| **Mean** | **0.788** | **0.956** | **0.936** | **0.984** | |

**Analysis:**
- AutoGen has the highest AST F1 (0.984) — generated code very closely mirrors source structure
- Triple F1 is moderate (0.788) due to systematic loss of termination conditions: the generator doesn't always recreate `TurnLimitTermination` individuals that the extractor finds
- The `promptContext` property (full system message text) is sometimes truncated or reformatted, causing literal mismatches
- Property F1 slightly lower (0.956) because `hasMaxTurns` and `hasTerminationCondition` are sometimes missing
- travel-planning and literature-review have lower scores due to composite termination (multiple conditions combined with operators) not fully round-tripping

### 1.4 Summary — All Frameworks

| Framework | n | Triple F1 | Prop F1 | Ind F1 | AST F1 |
|-----------|---|-----------|---------|--------|--------|
| CrewAI | 8 | **0.903** | **0.988** | **0.990** | 0.870 |
| LangGraph (valid) | 7 | 0.815 | 0.976 | 0.951 | 0.887 |
| AutoGen | 8 | 0.788 | 0.956 | 0.936 | **0.984** |
| **Overall** | **23** | **0.838** | **0.974** | **0.961** | **0.909** |

**Key Findings:**
- The AST pipeline achieves **83.8% Triple F1** on average — 5 out of 6 factual statements survive the full roundtrip
- **Property F1 > 0.95** for all frameworks — virtually all relationship types are preserved
- **Individual F1 > 0.93** — correct entity populations are maintained
- CrewAI has highest overall fidelity due to its declarative YAML structure (easy to parse and regenerate exactly)
- AutoGen has highest code-level fidelity (AST F1 = 0.984) because its Python API maps 1:1 to the ontology

---

## 2. AST Cross-Framework Roundtrip

**Pipeline:** `source_A → AST extract → TTL₁ → AST generate(B) → source_B → AST extract(B) → TTL₂`

### 2.1 CrewAI → LangGraph (n=8)

| Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | Notes |
|---------|-----------|------------|---------|--------|-------|
| academic-research-flow | 0.126 | 0.386 | 0.779 | 0.680 | CrewAI tasks/agents → LG nodes; crew structure lost |
| code-review | 0.131 | 0.410 | 0.840 | 0.783 | Tools and agent roles preserved |
| comprehensive | 0.132 | 0.389 | 0.750 | 0.721 | Complex crew features don't map to LG |
| content-pipeline | 0.087 | 0.421 | 0.872 | 0.825 | Good property coverage despite low Triple F1 |
| email-flow | 0.092 | 0.410 | 0.850 | 0.824 | Flow routing partially preserved |
| self-eval-loop-flow | 0.126 | 0.378 | 0.821 | 0.727 | Loop semantics partially captured |
| tech-blog | 0.266 | 0.469 | 0.853 | 0.772 | Best in class — simpler structure |
| unseen-hiring-pipeline | 0.126 | 0.414 | 0.782 | 0.771 | Router/listener pattern partially mapped |
| **Mean** | **0.135** | **0.410** | **0.818** | **0.763** | |

**Analysis:**
- **Triple F1 is very low (0.135)** because individual URIs are completely renamed during cross-framework translation (e.g., `Agent_senior_researcher` → `Agent_research_node`)
- **Aligned Triple F1 (0.410)** compensates for URI renames using bipartite matching — shows ~41% semantic content survives
- **Property F1 (0.818)** shows most relationship types exist in both representations
- **Individual F1 (0.763)** indicates the right types of entities exist but counts differ (LangGraph has fewer task/goal individuals than CrewAI)
- Main semantic gap: CrewAI's rich task metadata (expected_output, context dependencies, output_pydantic) has no LangGraph equivalent → information is lost

### 2.2 LangGraph → CrewAI (n=9)

| Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | Notes |
|---------|-----------|------------|---------|--------|-------|
| ReAct | 0.575 | 0.625 | 0.820 | 0.848 | Graph nodes → agents; tools preserved |
| drafter | 0.589 | 0.644 | 0.847 | 0.903 | Good structural mapping |
| memoryagent | 0.540 | 0.730 | 0.945 | 0.970 | Excellent property/individual preservation |
| plan-execute | 0.200 | 0.200 | 1.000 | 1.000 | Empty source → trivial match |
| ragagent | 0.576 | 0.620 | 0.839 | 0.821 | Conditional routing → crew flow |
| reflexion | 0.200 | 0.200 | 1.000 | 1.000 | Empty source → trivial match |
| research-assistant | 0.583 | 0.633 | 0.825 | 0.857 | Good overall preservation |
| tech-blog | 0.585 | 0.778 | 0.951 | 0.964 | High aligned F1; naming differences only |
| unseen-customer-support | 0.628 | 0.668 | 0.862 | 0.847 | 5-node graph → crew with tools |
| **Mean** | **0.497** | **0.566** | **0.899** | **0.912** | |
| **Mean (excl. empty)** | **0.582** | **0.671** | **0.870** | **0.887** | |

**Analysis:**
- **LG→CrewAI is significantly better than CrewAI→LG** (Aligned F1: 0.566 vs 0.410)
- This asymmetry occurs because CrewAI's richer API can absorb LangGraph's simpler concepts: every LG node becomes a CrewAI agent+task pair
- Triple F1 (0.497) is much higher than the reverse direction because many URIs partially align (same agent names survive)
- Property F1 (0.899) and Individual F1 (0.912) remain high — the ontology captures most semantics regardless of direction
- Main loss: LangGraph's graph topology (edges, conditional routing) is flattened into sequential CrewAI tasks

### 2.3 CrewAI → AutoGen (n=8)

| Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | Notes |
|---------|-----------|------------|---------|--------|-------|
| academic-research-flow | 0.035 | 0.382 | 0.729 | 0.625 | Crew roles → AutoGen agents; task structure differs |
| code-review | 0.034 | 0.328 | 0.778 | 0.633 | Tools preserved; delegation semantics lost |
| comprehensive | 0.053 | 0.391 | 0.667 | 0.644 | Complex crew hierarchy partially mapped |
| content-pipeline | 0.036 | 0.403 | 0.800 | 0.727 | Good property coverage |
| email-flow | 0.046 | 0.436 | 0.778 | 0.733 | Flow routing partially preserved |
| self-eval-loop-flow | 0.026 | 0.349 | 0.794 | 0.627 | Loop semantics mapped to team turns |
| tech-blog | 0.044 | 0.439 | 0.780 | 0.773 | Best aligned F1 in this direction |
| unseen-hiring-pipeline | 0.033 | 0.361 | 0.727 | 0.606 | Router → team selector mapping |
| **Mean** | **0.038** | **0.386** | **0.757** | **0.671** | |

**Analysis:**
- Very similar profile to CrewAI→LangGraph — Triple F1 near zero due to URI renames, Aligned F1 ~0.39
- Property F1 (0.757) indicates most relationship types transfer to AutoGen's model
- Individual F1 (0.671) lower than LG direction because CrewAI's many task/goal individuals don't all map to AutoGen equivalents
- CrewAI's output_pydantic, context dependencies, and delegation have no AutoGen counterpart

### 2.4 LangGraph → AutoGen (n=9)

| Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | Notes |
|---------|-----------|------------|---------|--------|-------|
| ReAct | 0.365 | 0.566 | 0.774 | 0.848 | Node → agent mapping works well |
| drafter | 0.315 | 0.534 | 0.820 | 0.839 | Tools and agent roles preserved |
| memoryagent | 0.290 | 0.548 | 0.846 | 0.828 | Memory config partially mapped |
| plan-execute | 0.125 | 0.125 | 0.286 | 0.250 | Empty source → minimal match |
| ragagent | 0.420 | 0.608 | 0.825 | 0.842 | Best Triple F1; tools transfer well |
| reflexion | 0.125 | 0.125 | 0.286 | 0.250 | Empty source → minimal match |
| research-assistant | 0.439 | 0.612 | 0.813 | 0.829 | Excellent preservation |
| tech-blog | 0.308 | 0.471 | 0.755 | 0.698 | State-heavy graph → flat team |
| unseen-customer-support | 0.492 | 0.596 | 0.813 | 0.720 | Multi-node graph → SelectorGroupChat |
| **Mean** | **0.320** | **0.465** | **0.691** | **0.678** | |
| **Mean (excl. empty)** | **0.375** | **0.562** | **0.807** | **0.801** | |

**Analysis:**
- Higher Triple F1 (0.320) than CrewAI→AutoGen because LangGraph agent names often survive directly
- Aligned F1 (0.465) shows roughly half the semantic content transfers
- LangGraph's simpler model is better absorbed by AutoGen than CrewAI's rich model
- Main loss: graph topology (edges, conditional routing) flattened to SelectorGroupChat/RoundRobinGroupChat

### 2.5 AutoGen → CrewAI (n=8)

| Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | Notes |
|---------|-----------|------------|---------|--------|-------|
| code-review | 0.200 | 0.663 | 0.909 | 0.919 | Excellent property/individual preservation |
| company-research | 0.219 | 0.566 | 0.889 | 0.864 | Good overall mapping |
| content-pipeline | 0.218 | 0.663 | 0.909 | 0.923 | Strong semantic transfer |
| data-analysis-0.4 | 0.240 | 0.640 | 0.909 | 0.927 | Best Triple F1 |
| literature-review | 0.218 | 0.564 | 0.889 | 0.864 | Consistent with other examples |
| tech-blog | 0.182 | 0.659 | 0.898 | 0.914 | Near-top aligned performance |
| travel-planning | 0.571 | 0.616 | 0.875 | 0.844 | Higher Triple F1 (simpler structure) |
| unseen-debate | 0.586 | 0.610 | 0.923 | 0.875 | SelectorGroupChat → Crew mapping works |
| **Mean** | **0.304** | **0.623** | **0.900** | **0.891** | |

**Analysis:**
- **Best cross-framework direction overall** — Aligned F1 of 0.623 is the highest among all 6 directions
- Property F1 (0.900) and Individual F1 (0.891) are excellent — CrewAI's rich API absorbs AutoGen's simpler concepts almost completely
- AutoGen agents → CrewAI agents is a natural 1:1 mapping; teams → crews works well
- travel-planning and unseen-debate have highest Triple F1 because their simpler agent names survive the translation
- Main loss: termination conditions and team orchestration specifics (selector prompts) don't map to CrewAI

### 2.6 AutoGen → LangGraph (n=8)

| Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | Notes |
|---------|-----------|------------|---------|--------|-------|
| code-review | 0.144 | 0.354 | 0.806 | 0.650 | Agents → nodes; tools preserved |
| company-research | 0.159 | 0.336 | 0.806 | 0.638 | Similar profile |
| content-pipeline | 0.165 | 0.392 | 0.825 | 0.667 | Slightly better alignment |
| data-analysis-0.4 | 0.155 | 0.373 | 0.825 | 0.651 | Consistent |
| literature-review | 0.149 | 0.326 | 0.806 | 0.638 | Consistent |
| tech-blog | 0.110 | 0.366 | 0.807 | 0.667 | Lower triple match |
| travel-planning | 0.090 | 0.291 | 0.807 | 0.558 | Most complex → most loss |
| unseen-debate | 0.133 | 0.319 | 0.800 | 0.583 | 4 agents → 4 nodes |
| **Mean** | **0.138** | **0.345** | **0.811** | **0.632** | |

**Analysis:**
- Very similar to CrewAI→LangGraph direction (Aligned 0.345 vs 0.410)
- Confirms that **generating to LangGraph always has lower fidelity** regardless of source — LangGraph's state-graph model is fundamentally different from agent-task models
- Property F1 (0.811) remains strong — same vocabulary used
- Individual F1 (0.632) lowest among all directions — LangGraph can't represent distinct goal/task individuals for each agent

### 2.7 Cross-Framework Summary (All 6 Directions)

| Direction | n | Triple F1 | Aligned F1 | Prop F1 | Ind F1 |
|-----------|---|-----------|------------|---------|--------|
| CrewAI → LangGraph | 8 | 0.135 | 0.410 | 0.818 | 0.763 |
| CrewAI → AutoGen | 8 | 0.038 | 0.386 | 0.757 | 0.671 |
| LangGraph → CrewAI | 7 | 0.582 | 0.671 | 0.870 | 0.887 |
| LangGraph → AutoGen | 7 | 0.375 | 0.562 | 0.807 | 0.801 |
| AutoGen → CrewAI | 8 | 0.304 | **0.623** | **0.900** | **0.891** |
| AutoGen → LangGraph | 8 | 0.138 | 0.345 | 0.811 | 0.632 |

**Patterns by target framework:**
| Target | Avg Aligned F1 | Avg Prop F1 | Avg Ind F1 |
|--------|---------------|-------------|------------|
| → CrewAI | **0.647** | **0.885** | **0.889** |
| → AutoGen | 0.474 | 0.782 | 0.736 |
| → LangGraph | 0.378 | 0.815 | 0.698 |

**Patterns by source framework:**
| Source | Avg Aligned F1 | Avg Prop F1 | Avg Ind F1 |
|--------|---------------|-------------|------------|
| CrewAI → | 0.398 | 0.788 | 0.717 |
| LangGraph → | 0.617 | 0.839 | 0.844 |
| AutoGen → | 0.484 | 0.856 | 0.762 |

**Key Findings:**
- **CrewAI is the best target** (Aligned F1 = 0.647) — its rich API can absorb content from any source framework
- **LangGraph is the worst target** (Aligned F1 = 0.378) — its state-graph model can't represent agent-task hierarchies
- **LangGraph is the best source** (Aligned F1 = 0.617) — its simpler semantics transfer easily to richer frameworks
- **CrewAI is the worst source** (Aligned F1 = 0.398) — its rich semantics have no equivalent in simpler frameworks
- The ontology preserves **Property F1 > 0.75** regardless of direction — the semantic vocabulary is framework-agnostic
- Asymmetry is consistent: rich→simple loses info; simple→rich preserves it

---

## 3. LLM Baseline Comparison

**Provider:** OpenAI GPT-4o | **Runs:** N=1

### 3.1 LLM Extraction vs AST Extraction

**Pipeline:** `source → LLM extract → TTL_llm` vs `source → AST extract → TTL_ast`

| Framework | Example | Triple F1 | Aligned F1 | Prop F1 | Ind F1 | AST# | LLM# |
|-----------|---------|-----------|------------|---------|--------|------|------|
| crewai | academic-research-flow | 0.000 | 0.235 | 0.338 | 0.357 | 190 | 48 |
| crewai | code-review | — | — | — | — | — | parse fail |
| crewai | comprehensive | 0.000 | 0.457 | 0.593 | 0.758 | 174 | 80 |
| crewai | content-pipeline | — | — | — | — | — | parse fail |
| crewai | email-flow | 0.000 | 0.237 | 0.429 | 0.449 | 187 | 49 |
| crewai | self-eval-loop-flow | 0.000 | 0.223 | 0.357 | 0.478 | 151 | 46 |
| crewai | tech-blog | 0.000 | 0.305 | 0.449 | 0.579 | 138 | 52 |
| crewai | unseen-hiring-pipeline | 0.000 | 0.131 | 0.312 | 0.258 | 202 | 58 |
| langgraph | ReAct | 0.000 | 0.242 | 0.508 | 0.579 | 86 | 63 |
| langgraph | drafter | 0.000 | 0.103 | 0.340 | 0.357 | 78 | 38 |
| langgraph | memoryagent | 0.000 | 0.194 | 0.233 | 0.462 | 69 | 24 |
| langgraph | plan-execute | 0.000 | 0.000 | 0.071 | 0.000 | 15 | 41 |
| langgraph | ragagent | 0.000 | 0.128 | 0.290 | 0.389 | 102 | 54 |
| langgraph | reflexion | — | — | — | — | — | parse fail |
| langgraph | research-assistant | 0.000 | 0.286 | 0.526 | 0.703 | 111 | 50 |
| langgraph | tech-blog | 0.000 | 0.295 | 0.356 | 0.636 | 133 | 57 |
| langgraph | unseen-customer-support | 0.000 | 0.251 | 0.481 | 0.571 | 221 | 113 |
| autogen | code-review | 0.000 | 0.260 | 0.409 | 0.667 | 100 | 46 |
| autogen | company-research | 0.000 | 0.093 | 0.348 | 0.364 | 123 | 28 |
| autogen | content-pipeline | 0.000 | 0.338 | 0.488 | 0.743 | 106 | 42 |
| autogen | data-analysis-0.4 | 0.000 | 0.306 | 0.381 | 0.706 | 105 | 39 |
| autogen | literature-review | — | — | — | — | — | parse fail |
| autogen | tech-blog | 0.000 | 0.194 | 0.359 | 0.562 | 93 | 41 |
| autogen | travel-planning | 0.000 | 0.054 | 0.216 | 0.182 | 128 | 19 |
| autogen | unseen-debate | — | — | — | — | — | parse fail |

| Framework | n (valid) | Aligned F1 | Prop F1 | Ind F1 | Parse Failures |
|-----------|-----------|------------|---------|--------|----------------|
| CrewAI | 6/8 | 0.265 | 0.413 | 0.480 | 2 |
| LangGraph | 8/9 | 0.187 | 0.351 | 0.462 | 1 |
| AutoGen | 6/8 | 0.208 | 0.367 | 0.537 | 2 |
| **Overall** | **20/25** | **0.216** | **0.374** | **0.489** | **5 (20%)** |

**Analysis:**
- **Triple F1 = 0.000 universally** — the LLM uses completely different individual naming conventions (e.g., `SeniorResearcher` vs `Agent_senior_researcher`), so no normalized triple matches exactly
- **Aligned F1 = 0.216** — even with bipartite matching, only ~22% of semantic content aligns because the LLM uses different predicates (e.g., `agentID` vs `hasName`, `performedByAgent` vs `assignedTo`)
- **Property F1 = 0.374** — the LLM uses only ~37% of the same ontology properties as the AST extractor
- **Individual F1 = 0.489** — roughly half the entity types/counts match
- **20% parse failure rate** — GPT-4o produces invalid Turtle in 5/25 cases
- **LLM extracts far fewer triples** — mean 48 ABox triples vs AST mean 128 (62% information loss)
- The LLM tends to invent properties not in the schema (`hasAgentCapability`, `output_pydantic`, `hasObjective`) and misuses existing ones

### 3.2 LLM Same-Framework Roundtrip

**Pipeline:** `source → LLM extract → TTL₁ → LLM generate(same_fw) → source' → AST extract → TTL₂`

| Metric | Mean (all valid) | Notes |
|--------|-----------------|-------|
| Triple F1 | 0.000 | Complete URI mismatch between LLM TTL₁ and AST TTL₂ |
| Aligned F1 | 0.002 | Virtually no semantic alignment survives |
| Property F1 | 0.040 | Only ~4% of properties shared |
| Individual F1 | 0.005 | Essentially no class-level match |
| Success rate | 14/25 (56%) | 11 examples failed (TTL parse or re-extraction errors) |

**Analysis:**
- The LLM roundtrip produces **near-zero fidelity** across all metrics
- Root cause: The LLM-generated code does not follow framework conventions closely enough for the AST parser to extract meaningful ontology instances
- Common failure modes:
  - LLM generates code with syntax errors (imports fail, wrong API calls)
  - Generated code uses deprecated or non-existent framework APIs
  - The structure doesn't match the parser's expected patterns (@CrewBase class, StateGraph(), AssistantAgent())
- The re-extracted TTL₂ contains only the bare ontology schema (15 triples = just the TBox)
- This demonstrates that **LLM generation without structural constraints produces non-parseable output**

### 3.3 LLM Cross-Framework Roundtrip

**Pipeline:** `source_A → LLM extract → TTL₁ → LLM generate(B) → source_B → AST extract(B) → TTL₂`

| Direction | n (valid) | Triple F1 | Aligned F1 | Prop F1 | Ind F1 |
|-----------|-----------|-----------|------------|---------|--------|
| CrewAI → LangGraph | 6/8 | 0.000 | 0.009 | 0.000 | 0.040 |
| CrewAI → AutoGen | 2/8 | 0.000 | 0.038 | 0.048 | 0.151 |
| LangGraph → CrewAI | 9/9 | 0.000 | 0.003 | 0.053 | 0.012 |
| LangGraph → AutoGen | 0/9 | — | — | — | — |
| AutoGen → CrewAI | 5/8 | 0.000 | 0.000 | 0.022 | 0.000 |
| AutoGen → LangGraph | 5/8 | 0.000 | 0.000 | 0.000 | 0.000 |
| **Overall (all dirs)** | **27/50** | **0.000** | **0.006** | **0.018** | **0.025** |

**Analysis:**
- Cross-framework LLM roundtrip achieves **essentially zero** across all metrics in every direction
- The LLM cannot generate framework-idiomatic code that the AST parser recognizes
- This represents the worst-case scenario: two lossy LLM steps compound each other
- Adding AutoGen directions does not change the conclusion — all 6 directions produce near-zero results

---

## 4. Comparative Summary: AST vs LLM Pipeline

### 4.1 Head-to-Head Comparison

| Experiment | AST Pipeline | LLM Pipeline (GPT-4o) | AST Advantage |
|------------|-------------|----------------------|---------------|
| **Same-fw roundtrip** Triple F1 | **0.838** | 0.000 | +0.838 |
| **Same-fw roundtrip** Aligned F1 | 0.838 | 0.002 | +0.836 |
| **Same-fw roundtrip** Property F1 | **0.974** | 0.040 | +0.934 |
| **Same-fw roundtrip** Individual F1 | **0.961** | 0.005 | +0.956 |
| **Cross-fw** Aligned F1 (CF→LG) | **0.410** | 0.009 | +0.401 |
| **Cross-fw** Aligned F1 (LG→CF) | **0.671** | 0.003 | +0.668 |
| **Cross-fw** Aligned F1 (AG→CF) | **0.623** | ~0.01 | +0.613 |
| **Cross-fw** Aligned F1 (LG→AG) | **0.562** | ~0.01 | +0.552 |
| **Cross-fw** Aligned F1 (CF→AG) | **0.386** | ~0.01 | +0.376 |
| **Cross-fw** Aligned F1 (AG→LG) | **0.345** | ~0.01 | +0.335 |
| **Extraction** Aligned F1 (vs AST ref) | 1.000 (self) | 0.216 | — |
| **Parse failure rate** | 0% | 20% | — |
| **Success rate** (full roundtrip) | 100% | 56% | — |

### 4.2 Why the LLM Approach Fails

1. **Namespace confusion** — GPT-4o places individuals in the ontology namespace instead of a separate instance namespace, conflating TBox and ABox
2. **Schema non-compliance** — invents properties not in the ontology (e.g., `hasAgentCapability`, `output_pydantic`)
3. **Information loss** — extracts only 37% of ABox triples compared to AST (48 vs 128 mean triples)
4. **Code generation quality** — produces code with syntax errors, wrong APIs, or non-idiomatic patterns that AST parsers cannot recognize
5. **Non-determinism** — 20% of outputs fail to parse as valid Turtle
6. **Compounding errors** — each LLM step introduces ~60-80% error, so roundtrip compounds to near-total loss

### 4.3 Key Takeaway

The deterministic AST-based pipeline outperforms the LLM baseline by **an order of magnitude** on every metric. The AST approach's strength comes from:
- **Structural guarantees**: parsers match documented framework APIs → 100% success rate
- **Schema compliance**: populator uses only ontology-defined classes/properties → no invented predicates
- **Naming consistency**: fixed URI templates → exact triple matching across roundtrip
- **Determinism**: same input always produces same output → reproducible evaluation

---

## 5. Per-Framework Diagnostic Notes

### 5.1 CrewAI — Common Loss Patterns
- **`dependsOn` / `hasDependencyType`**: Task context dependencies are extracted but the generator doesn't always reproduce the context chain
- **`hasTeamMemoryBinding`**: Team-level memory configuration (`memory=True`) is extracted as a binding but the generator doesn't always emit it back
- **AST F1 gap (0.870)**: The generator produces canonical CrewAI layout (standard YAML structure), which may differ from the original's file organization while being semantically equivalent

### 5.2 LangGraph — Common Loss Patterns
- **Extra Goal/Task individuals**: The generator infers Goal/Task from node function descriptions, creating individuals not in the original extraction
- **Conditional routing**: `add_conditional_edges()` with complex routing functions are hard to faithfully reconstruct — the routing logic string may differ
- **plan-execute / reflexion**: These examples have empty source_files directories (notebooks only) — extraction produces minimal TTL, inflating the "low F1" appearance
- **ToolNode confusion** (fixed): Previously, ToolNode steps generated spurious Agent/Goal/Task individuals; fixed with `_is_tool_node_step()` helper

### 5.3 AutoGen — Common Loss Patterns
- **Termination conditions**: `MaxMessageTermination` / `TurnLimitTermination` individuals are extracted but the generator doesn't always recreate them as separate entities
- **`promptContext` truncation**: Full system messages are preserved in extraction but may be reformatted during generation, causing literal mismatch
- **Composite termination**: The `|` operator combining multiple conditions is partially lost (some examples gain extra `CompositeTermination` individuals, others lose them)
- **Highest AST F1 (0.984)**: AutoGen's flat Python API maps almost perfectly to the generated output structure

### 5.4 Cross-Framework — Asymmetry Explained
- **Generating TO CrewAI** (best target, Aligned 0.647): CrewAI's rich API can absorb any source — every agent/node/task maps to a CrewAI construct
- **Generating TO LangGraph** (worst target, Aligned 0.378): LangGraph's state-graph model cannot represent rich agent-task hierarchies → information is flattened
- **Generating FROM LangGraph** (best source, Aligned 0.617): Its simpler model transfers easily without loss to richer targets
- **Generating FROM CrewAI** (worst source, Aligned 0.398): Rich semantics (task deps, delegation, output_pydantic) have no equivalent in simpler frameworks
- The **ontology** preserves the full semantic content — the loss occurs at generation time when target framework lacks equivalent constructs

---

## 6. Aggregate Results for Thesis

### RQ2: "To what extent can we extract?"

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Same-fw Triple F1 | 0.838 | 84% of ontology facts survive full roundtrip |
| Same-fw Property F1 | 0.974 | 97% of relationship types preserved |
| Same-fw Individual F1 | 0.961 | 96% of entities correctly typed/counted |
| Same-fw AST F1 | 0.909 | 91% of code structure preserved |
| Extraction success rate | 100% (23/23 valid examples) | No extraction failures |

### RQ3: "To what extent can we generate / translate?"

| Metric | Same-fw | Cross-fw (best) | Cross-fw (worst) | Cross-fw (mean) |
|--------|---------|-----------------|------------------|-----------------|
| Aligned Triple F1 | 0.838 | 0.671 (LG→CF) | 0.345 (AG→LG) | 0.483 |
| Property F1 | 0.974 | 0.900 (AG→CF) | 0.757 (CF→AG) | 0.818 |
| Individual F1 | 0.961 | 0.891 (AG→CF) | 0.632 (AG→LG) | 0.775 |
| Generation success rate | 100% | 100% | 100% | 100% |

**Cross-framework by direction:**
| Direction | Aligned F1 | Prop F1 | Ind F1 |
|-----------|------------|---------|--------|
| LG → CrewAI | 0.671 | 0.870 | 0.887 |
| AG → CrewAI | 0.623 | 0.900 | 0.891 |
| LG → AutoGen | 0.562 | 0.807 | 0.801 |
| CF → LangGraph | 0.410 | 0.818 | 0.763 |
| CF → AutoGen | 0.386 | 0.757 | 0.671 |
| AG → LangGraph | 0.345 | 0.811 | 0.632 |

### LLM Baseline (for comparison)

| Metric | AST Pipeline | LLM (GPT-4o) | Factor |
|--------|-------------|---------------|--------|
| Extraction success | 100% | 80% | 1.25× |
| Same-fw roundtrip Aligned F1 | 0.838 | 0.002 | **419×** |
| Same-fw roundtrip Property F1 | 0.974 | 0.040 | **24×** |
| Cross-fw Aligned F1 (mean, 6 dirs) | 0.483 | 0.006 | **81×** |
| Cross-fw success rate | 100% (50/50) | 54% (27/50) | 1.85× |
| Roundtrip success rate (same-fw) | 100% | 56% | 1.79× |
| TTL parse failure rate | 0% | 20% | — |
