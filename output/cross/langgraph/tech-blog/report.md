# Roundtrip — langgraph/tech-blog

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/tech-blog/source_files`
- target framework: `crewai`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/cross/langgraph/tech-blog`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/langgraph/tech-blog/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/langgraph/tech-blog/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/cross/langgraph/tech-blog/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=0.966 R=0.966 F1=0.966
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.630 R=0.630 F1=0.630
- **literal_overlap**: 0.857

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 24
- avg score: 0.986

## AST diff (source vs generated)
- overall: P=0.431 R=0.432 F1=0.431
  - imports: ref=7 cand=4 F1=0.364
  - class_bases: ref=1 cand=3 F1=0.0
  - functions: ref=5 cand=8 F1=0.462
  - graph_calls: ref=7 cand=0 F1=0.0
  - state_annotations: ref=5 cand=5 F1=1.0
  - decorators: ref=0 cand=6 F1=0.0
  - decorator_args: ref=0 cand=0 F1=1.0
  - classes: ref=1 cand=2 F1=0.0
  - state_fields: ref=5 cand=5 F1=1.0

## Execution trace
- skipped

## Mapping conformance (CrewAI Flow ↔ LangGraph)
- direction: lg_to_cf
- overall: 0.561
- applicable rules: 6
  - graph_class: lg=1 cf=1 score=1.0
  - node_to_decorated: lg=3 cf=3 score=1.0
  - entry_point: lg=0 cf=1 score=0.0
  - sequential_edge: lg=3 cf=2 score=0.667
  - conditional: lg=0 cf=0 score=None
  - state_reducer: lg=1 cf=5 score=0.2
  - kickoff: lg=1 cf=2 score=0.5
  - fan_in: lg=0 cf=0 score=None
  - fan_in_or: lg=0 cf=0 score=None
