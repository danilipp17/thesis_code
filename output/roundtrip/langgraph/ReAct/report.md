# Roundtrip — langgraph/ReAct

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/ReAct`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ReAct`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ReAct/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ReAct/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/ReAct/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=0.909 R=1.000 F1=0.952
- **property**: P=0.944 R=1.000 F1=0.971
- **triple**: P=0.670 R=0.716 F1=0.692
- **literal_overlap**: 0.724

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 15
- avg score: 1.0

## AST diff (source vs generated)
- overall: P=0.693 R=0.7 F1=0.696
  - decorators: ref=1 cand=1 F1=1.0
  - functions: ref=6 cand=5 F1=0.545
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_fields: ref=1 cand=1 F1=1.0
  - state_annotations: ref=1 cand=1 F1=1.0
  - graph_calls: ref=5 cand=5 F1=0.8
  - imports: ref=5 cand=6 F1=0.909
  - classes: ref=1 cand=1 F1=0.0

## Execution trace
- skipped
