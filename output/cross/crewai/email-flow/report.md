# Roundtrip — crewai/email-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/email-flow/source_files`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/email-flow`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/email-flow/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/email-flow/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/crewai/email-flow/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=0.964 R=0.692 F1=0.806
- **property**: P=1.000 R=0.795 F1=0.886
- **triple**: P=0.109 R=0.075 F1=0.089
- **literal_overlap**: 0.278

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 19
- avg score: 0.803

## AST diff (source vs generated)
- overall: P=0.241 R=0.272 F1=0.256
  - imports: ref=10 cand=6 F1=0.25
  - graph_calls: ref=0 cand=5 F1=0.0
  - decorators: ref=6 cand=1 F1=0.0
  - class_bases: ref=4 cand=1 F1=0.0
  - functions: ref=12 cand=6 F1=0.333
  - decorator_args: ref=2 cand=0 F1=0.0
  - state_fields: ref=2 cand=3 F1=0.8
  - state_annotations: ref=2 cand=3 F1=0.8
  - classes: ref=4 cand=1 F1=0.0

## Execution trace
- skipped

## Mapping conformance (CrewAI Flow ↔ LangGraph)
- direction: cf_to_lg
- overall: 0.75
- applicable rules: 6
  - graph_class: lg=1 cf=1 score=1.0
  - node_to_decorated: lg=3 cf=2 score=0.667
  - entry_point: lg=1 cf=1 score=1.0
  - sequential_edge: lg=1 cf=1 score=1.0
  - conditional: lg=0 cf=0 score=None
  - state_reducer: lg=1 cf=2 score=0.5
  - kickoff: lg=1 cf=3 score=0.333
