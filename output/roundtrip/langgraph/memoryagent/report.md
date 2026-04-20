# Roundtrip — langgraph/memoryagent

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/memoryagent`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=0.933 R=1.000 F1=0.966
- **triple**: P=0.694 R=0.714 F1=0.704
- **literal_overlap**: 0.778

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 13
- avg score: 0.976

## AST diff (source vs generated)
- overall: P=0.778 R=0.722 F1=0.749
  - decorators: ref=0 cand=0 F1=1.0
  - functions: ref=1 cand=1 F1=1.0
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_fields: ref=1 cand=1 F1=1.0
  - state_annotations: ref=1 cand=1 F1=1.0
  - graph_calls: ref=3 cand=2 F1=0.8
  - imports: ref=6 cand=5 F1=0.909
  - classes: ref=1 cand=1 F1=0.0

## Execution trace
- skipped
