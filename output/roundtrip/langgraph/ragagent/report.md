# Roundtrip — langgraph/ragagent

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/ragagent`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ragagent`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ragagent/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ragagent/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ragagent/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=0.963 F1=0.981
- **property**: P=0.974 R=0.974 F1=0.974
- **triple**: P=0.771 R=0.765 F1=0.768
- **literal_overlap**: 0.719

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 21
- avg score: 0.982

## AST diff (source vs generated)
- overall: P=0.618 R=0.567 F1=0.591
  - decorators: ref=1 cand=1 F1=1.0
  - functions: ref=5 cand=3 F1=0.25
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_fields: ref=1 cand=1 F1=1.0
  - state_annotations: ref=1 cand=1 F1=1.0
  - graph_calls: ref=5 cand=5 F1=0.4
  - imports: ref=10 cand=6 F1=0.625
  - classes: ref=1 cand=1 F1=0.0

## Execution trace
- skipped
