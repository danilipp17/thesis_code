# OSCIN Evaluation Metrics — Extraction & Generation

## Overview

This document presents all metrics produced by the OSCIN evaluation pipeline across three experiment types:

1. **Extraction** (source code → TTL): intrinsic metrics measuring the size and richness of each knowledge graph (20 examples)
2. **Same-Framework Roundtrip** (source → TTL₁ → generate → re-extract → TTL₂): measures ontology preservation and code fidelity (20 examples)
3. **Cross-Framework Roundtrip** (source_A → TTL₁ → generate_B → re-extract_B → TTL₂): measures framework-agnostic portability (13 examples: 7 CrewAI→LangGraph, 6 LangGraph→CrewAI)

---

## Metric Legend

### Intrinsic Metrics (single TTL, no reference)

| Metric | Definition |
|--------|------------|
| **ABox Triples** | Instance-level RDF triples (excludes imported ontology schema). The actual semantic content about the extracted system. |
| **Individuals** | Count of distinct OWL named individuals (agents, tasks, tools, steps, etc.). |
| **Properties Used** | Number of distinct agentoscin properties exercised (e.g., `agentRole`, `nextStep`). |
| **Density** | `abox_triples / individuals` — average triples per entity. Measures annotation richness. |

### Pairwise Metrics (TTL₁ vs TTL₂ — roundtrip preservation)

| Metric | Definition |
|--------|------------|
| **Triple F1** | F1 over normalized (subject_local, predicate_local, object_repr) triples. Exact URI-name match. Measures full triple-level preservation. |
| **Aligned Triple F1** | Same as Triple F1, but after class-aware bipartite alignment of individuals (tolerates URI renames like `Agent_writer` → `Agent_content_writer`). |
| **Property F1** | F1 over the set of ontology properties used. Measures whether the same semantic dimensions survive. |
| **Individual F1** | F1 over typed individuals by class. Measures whether the same entities (same count per class) survive. |
| **Literal Overlap** | Jaccard overlap of normalized literal string values. Measures whether textual content (prompts, descriptions) survives. |
| **Fuzzy Avg Score** | Mean similarity of best-matched individual pairs (name + label similarity via SequenceMatcher). 1.0 = perfect name alignment. |

### Code-Level Metrics (generated source code)

| Metric | Definition |
|--------|------------|
| **Syntax Validity** | Fraction of generated `.py` files that parse without SyntaxError. |
| **AST F1** | F1 over structural AST features (class names, function names, decorators, state fields, imports) between original and generated code. |
| **AST Recall** | Fraction of original code features found in generated code (completeness). |
| **AST Precision** | Fraction of generated features that exist in original (spurious-free). |

### Cross-Framework Metric

| Metric | Definition |
|--------|------------|
| **Mapping Conformance** | Per-rule score: `min(src_count, tgt_count) / max(src_count, tgt_count)` averaged over canonical CrewAI↔LangGraph translation rules. Measures whether structural patterns are correctly translated. |

---

## 1. Extraction Results (RQ2)

### Per-Example Intrinsic Metrics

#### CrewAI (7 examples)

| Example | ABox Triples | Individuals | Properties | Density | Literals | Object Links |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| academic-research-flow | 190 | 44 | 53 | 4.32 | 83 | 102 |
| code-review | 196 | 41 | 44 | 4.78 | 88 | 103 |
| comprehensive | 174 | 40 | 55 | 4.35 | 75 | 94 |
| content-pipeline | 175 | 35 | 42 | 5.00 | 79 | 91 |
| email-flow | 187 | 38 | 44 | 4.92 | 84 | 98 |
| self-eval-loop-flow | 151 | 34 | 40 | 4.44 | 65 | 81 |
| tech-blog | 138 | 26 | 34 | 5.31 | 62 | 71 |

#### AutoGen (7 examples)

| Example | ABox Triples | Individuals | Properties | Density | Literals | Object Links |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| code-review | 100 | 20 | 30 | 5.00 | 43 | 52 |
| company-research | 123 | 25 | 30 | 4.92 | 58 | 60 |
| content-pipeline | 106 | 21 | 30 | 5.05 | 47 | 54 |
| data-analysis-0.4 | 105 | 22 | 30 | 4.77 | 46 | 54 |
| literature-review | 124 | 25 | 30 | 4.96 | 59 | 60 |
| tech-blog | 93 | 19 | 27 | 4.89 | 39 | 49 |
| travel-planning | 128 | 26 | 27 | 4.92 | 58 | 65 |

#### LangGraph (6 examples)

| Example | ABox Triples | Individuals | Properties | Density | Literals | Object Links |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| ReAct | 86 | 18 | 35 | 4.78 | 36 | 45 |
| drafter | 78 | 17 | 33 | 4.59 | 30 | 43 |
| memoryagent | 69 | 17 | 28 | 4.06 | 21 | 43 |
| ragagent | 102 | 22 | 35 | 4.64 | 40 | 57 |
| research-assistant | 111 | 24 | 36 | 4.63 | 46 | 60 |
| tech-blog | 133 | 28 | 31 | 4.75 | 49 | 79 |

### Extraction Aggregates

| Metric | CrewAI (n=7) | AutoGen (n=7) | LangGraph (n=6) | All (n=20) |
|--------|:---:|:---:|:---:|:---:|
| Mean ABox Triples | 173.0 | 111.3 | 96.5 | 128.4 |
| Mean Individuals | 36.9 | 22.6 | 21.0 | 27.1 |
| Mean Properties | 44.6 | 29.1 | 33.0 | 35.7 |
| Mean Density | 4.73 | 4.93 | 4.57 | 4.75 |
| Object Link Ratio | 0.53 | 0.51 | 0.57 | 0.53 |

---

## 2. Same-Framework Roundtrip Results (RQ2 + RQ3)

Pipeline: source → extract → TTL₁ → generate(same-fw) → re-extract → TTL₂

This measures: (a) how much semantic content survives a full round trip, and (b) whether the generated code is structurally faithful.

### Per-Example Results

#### CrewAI → CrewAI (7 examples)

| Example | Triple F1 | Property F1 | Individual F1 | Literal Overlap | Fuzzy Avg | AST F1 |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| academic-research-flow | 0.847 | 0.971 | 0.966 | 0.902 | 1.000 | 0.765 |
| code-review | 0.916 | 1.000 | 1.000 | 0.952 | 1.000 | 0.910 |
| comprehensive | 0.889 | 0.944 | 0.974 | 0.917 | 1.000 | 0.829 |
| content-pipeline | 0.911 | 1.000 | 1.000 | 0.944 | 1.000 | 0.895 |
| email-flow | 0.925 | 1.000 | 1.000 | 0.966 | 1.000 | 0.819 |
| self-eval-loop-flow | 0.914 | 1.000 | 1.000 | 0.980 | 1.000 | 0.924 |
| tech-blog | 0.913 | 1.000 | 1.000 | 1.000 | 1.000 | 0.972 |

#### AutoGen → AutoGen (7 examples)

| Example | Triple F1 | Property F1 | Individual F1 | Literal Overlap | Fuzzy Avg | AST F1 |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| code-review | 0.873 | 0.966 | 0.974 | 0.966 | 1.000 | 0.992 |
| company-research | 0.749 | 0.947 | 0.913 | 0.692 | 1.000 | — |
| content-pipeline | 0.871 | 0.966 | 0.976 | 0.939 | 1.000 | 0.986 |
| data-analysis-0.4 | 0.829 | 0.966 | 0.952 | 0.875 | 1.000 | 0.970 |
| literature-review | 0.709 | 0.935 | 0.898 | 0.650 | 1.000 | — |
| tech-blog | 0.863 | 0.962 | 0.973 | 0.960 | 1.000 | 0.989 |
| travel-planning | 0.683 | 0.929 | 0.880 | 0.656 | 0.968 | — |

Note: AST F1 is "—" for 3 AutoGen examples because the source is a Jupyter notebook (`.ipynb`), not `.py` files; the AST diff metric only compares `.py` files.

#### LangGraph → LangGraph (6 examples)

| Example | Triple F1 | Property F1 | Individual F1 | Literal Overlap | Fuzzy Avg | AST F1 |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| ReAct | 0.687 | 0.986 | 0.857 | 0.800 | 1.000 | 0.913 |
| drafter | 0.603 | 0.943 | 0.810 | 0.846 | 0.974 | 0.864 |
| memoryagent | 0.829 | 0.966 | 1.000 | 1.000 | 1.000 | 0.962 |
| ragagent | 0.762 | 0.944 | 0.875 | 0.880 | 1.000 | 0.814 |
| research-assistant | 0.846 | 1.000 | 0.980 | 0.879 | 1.000 | 0.803 |
| tech-blog | 0.871 | 0.969 | 0.933 | 1.000 | 1.000 | 0.915 |

### Same-Framework Roundtrip Aggregates

| Metric | CrewAI (n=7) | AutoGen (n=7) | LangGraph (n=6) | All (n=20) |
|--------|:---:|:---:|:---:|:---:|
| **Triple F1** | 0.902 | 0.797 | 0.766 | 0.824 |
| **Property F1** | 0.988 | 0.953 | 0.968 | 0.970 |
| **Individual F1** | 0.991 | 0.938 | 0.909 | 0.948 |
| **Literal Overlap** | 0.951 | 0.820 | 0.901 | 0.890 |
| **Fuzzy Avg Score** | 1.000 | 0.995 | 0.996 | 0.997 |
| **AST F1** | 0.873 (n=7) | 0.984 (n=4) | 0.878 (n=6) | 0.901 (n=17) |
| **Syntax Validity** | 41/41 (100%) | 12/12 (100%) | 10/10 (100%) | 63/63 (100%) |

---

## 3. Cross-Framework Roundtrip Results (RQ3)

Pipeline: source_A → extract → TTL₁ → generate(B) → re-extract(B) → TTL₂

This measures: how well the ontology-mediated translation preserves semantic content when switching frameworks.

### CrewAI → LangGraph (7 examples)

| Example | Triple F1 | Aligned Triple F1 | Property F1 | Individual F1 | Literal Overlap | Fuzzy Avg | Mapping Conf. |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| academic-research-flow | 0.126 | 0.386 | 0.779 | 0.680 | 0.279 | 0.873 | 0.632 |
| code-review | 0.131 | 0.410 | 0.840 | 0.783 | 0.242 | 0.823 | 0.616 |
| comprehensive | 0.132 | 0.389 | 0.750 | 0.721 | 0.283 | 0.857 | 0.721 |
| content-pipeline | 0.087 | 0.421 | 0.872 | 0.825 | 0.185 | 0.804 | 0.528 |
| email-flow | 0.092 | 0.410 | 0.850 | 0.824 | 0.259 | 0.821 | 0.583 |
| self-eval-loop-flow | 0.126 | 0.378 | 0.821 | 0.727 | 0.235 | 0.813 | 0.602 |
| tech-blog | 0.266 | 0.469 | 0.853 | 0.772 | 0.450 | 0.883 | 0.167 |

### LangGraph → CrewAI (6 examples)

| Example | Triple F1 | Aligned Triple F1 | Property F1 | Individual F1 | Literal Overlap | Fuzzy Avg | Mapping Conf. |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ReAct | 0.575 | 0.625 | 0.820 | 0.848 | 0.600 | 1.000 | 0.405 |
| drafter | 0.589 | 0.644 | 0.847 | 0.903 | 0.615 | 1.000 | 0.426 |
| memoryagent | 0.540 | 0.730 | 0.945 | 0.970 | 0.750 | 1.000 | 0.583 |
| ragagent | 0.576 | 0.620 | 0.839 | 0.821 | 0.640 | 1.000 | 0.444 |
| research-assistant | 0.583 | 0.633 | 0.825 | 0.857 | 0.576 | 1.000 | 0.522 |
| tech-blog | 0.585 | 0.778 | 0.951 | 0.964 | 0.852 | 1.000 | 0.561 |

### Cross-Framework Roundtrip Aggregates

| Metric | CrewAI→LangGraph (n=7) | LangGraph→CrewAI (n=6) |
|--------|:---:|:---:|
| **Triple F1** | 0.137 | 0.575 |
| **Aligned Triple F1** | 0.409 | 0.672 |
| **Property F1** | 0.823 | 0.871 |
| **Individual F1** | 0.762 | 0.894 |
| **Literal Overlap** | 0.276 | 0.672 |
| **Fuzzy Avg Score** | 0.839 | 1.000 |
| **Mapping Conformance** | 0.550 | 0.490 |

---

## 4. Summary Table: All Metrics at a Glance

### RQ2 — Extraction Fidelity ("To what extent can we extract?")

| Metric | CrewAI | AutoGen | LangGraph | Overall |
|--------|:---:|:---:|:---:|:---:|
| Extraction succeeds | 7/7 | 7/7 | 6/6 | **20/20 (100%)** |
| Mean ABox triples | 173.0 | 111.3 | 96.5 | **128.4** |
| Mean individuals | 36.9 | 22.6 | 21.0 | **27.1** |
| Mean properties used | 44.6 | 29.1 | 33.0 | **35.7** |
| Mean density | 4.73 | 4.93 | 4.57 | **4.75** |
| Roundtrip Triple F1 | 0.902 | 0.797 | 0.766 | **0.824** |
| Roundtrip Property F1 | 0.988 | 0.953 | 0.968 | **0.970** |
| Roundtrip Individual F1 | 0.991 | 0.938 | 0.909 | **0.948** |
| Roundtrip Literal Overlap | 0.951 | 0.820 | 0.901 | **0.890** |

### RQ3 — Generation Fidelity ("To what extent can we generate?")

| Metric | Same-FW | Cross-FW (CF→LG) | Cross-FW (LG→CF) |
|--------|:---:|:---:|:---:|
| Syntax validity | **63/63 (100%)** | all valid | all valid |
| AST F1 (code structure) | **0.901** | n/a (different FW) | n/a |
| Triple F1 (ontology) | **0.824** | 0.137 | 0.575 |
| Aligned Triple F1 | **0.824** | 0.409 | 0.672 |
| Property F1 | **0.970** | 0.823 | 0.871 |
| Individual F1 | **0.948** | 0.762 | 0.894 |
| Fuzzy Avg Score | **0.997** | 0.839 | 1.000 |
| Mapping Conformance | n/a | **0.550** | **0.490** |
