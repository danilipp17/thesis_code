# Roundtrip — langgraph/tech-blog

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/tech-blog/source_files`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/tech-blog`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/tech-blog/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/tech-blog/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/tech-blog/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=0.906 R=1.000 F1=0.951
- **property**: P=0.939 R=1.000 F1=0.969
- **triple**: P=0.782 R=0.833 F1=0.807
- **literal_overlap**: 0.929

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 24
- avg score: 0.986

## AST diff (source vs generated)
- overall: P=0.756 R=0.654 F1=0.701
  - decorators: ref=0 cand=0 F1=1.0
  - functions: ref=5 cand=3 F1=0.75
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_fields: ref=5 cand=5 F1=1.0
  - state_annotations: ref=5 cand=5 F1=1.0
  - graph_calls: ref=7 cand=5 F1=0.667
  - imports: ref=7 cand=5 F1=0.833
  - classes: ref=1 cand=1 F1=0.0

## Execution trace
- skipped
