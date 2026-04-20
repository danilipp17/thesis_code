# Roundtrip — autogen/code-review

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/autogen/code-review/source_files`
- target framework: `autogen`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/code-review`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/code-review/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/code-review/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/code-review/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=0.962 F1=0.980
- **property**: P=1.000 R=0.966 F1=0.982
- **triple**: P=0.822 R=0.800 F1=0.811
- **literal_overlap**: 0.933

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 21
- avg score: 0.985

## AST diff (source vs generated)
- overall: P=1.0 R=0.984 F1=0.992
  - decorators: ref=0 cand=0 F1=1.0
  - functions: ref=2 cand=2 F1=1.0
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=0 cand=0 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - state_annotations: ref=0 cand=0 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=7 cand=6 F1=0.923
  - classes: ref=0 cand=0 F1=1.0

## Execution trace
- skipped
