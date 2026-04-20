# Roundtrip — langgraph/drafter

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/drafter`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=0.167 F1=0.286
- **property**: P=1.000 R=0.152 F1=0.263
- **triple**: P=0.280 R=0.087 F1=0.133
- **literal_overlap**: 0.192

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 3
- avg score: 0.861

## AST diff (source vs generated)
- overall: P=0.444 R=0.281 F1=0.344
  - decorators: ref=1 cand=1 F1=1.0
  - functions: ref=6 cand=2 F1=0.5
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=0 F1=0.0
  - state_fields: ref=1 cand=0 F1=0.0
  - state_annotations: ref=1 cand=0 F1=0.0
  - graph_calls: ref=5 cand=0 F1=0.0
  - imports: ref=5 cand=1 F1=0.333
  - classes: ref=1 cand=0 F1=0.0

## Execution trace
- skipped
