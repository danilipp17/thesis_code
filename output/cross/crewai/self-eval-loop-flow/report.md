# Roundtrip — crewai/self-eval-loop-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/self-eval-loop-flow/source_files`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/self-eval-loop-flow`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/self-eval-loop-flow/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/self-eval-loop-flow/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/self-eval-loop-flow/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=0.667 R=0.757 F1=0.709
- **property**: P=0.895 R=0.850 F1=0.872
- **triple**: P=0.117 R=0.152 F1=0.132
- **literal_overlap**: 0.326

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 22
- avg score: 0.812

## AST diff (source vs generated)
- overall: P=0.315 R=0.27 F1=0.291
  - imports: ref=7 cand=6 F1=0.462
  - decorator_args: ref=3 cand=0 F1=0.0
  - decorators: ref=7 cand=1 F1=0.0
  - state_fields: ref=6 cand=6 F1=0.833
  - functions: ref=12 cand=6 F1=0.444
  - classes: ref=7 cand=1 F1=0.0
  - state_annotations: ref=6 cand=6 F1=0.833
  - graph_calls: ref=0 cand=10 F1=0.0
  - class_bases: ref=7 cand=1 F1=0.0

## Execution trace
- skipped

## Mapping conformance (CrewAI Flow ↔ LangGraph)
- direction: cf_to_lg
- overall: 0.674
- applicable rules: 7
  - graph_class: lg=1 cf=1 score=1.0
  - node_to_decorated: lg=5 cf=4 score=0.8
  - entry_point: lg=1 cf=1 score=1.0
  - sequential_edge: lg=4 cf=2 score=0.5
  - conditional: lg=1 cf=1 score=1.0
  - state_reducer: lg=1 cf=6 score=0.167
  - kickoff: lg=1 cf=4 score=0.25
