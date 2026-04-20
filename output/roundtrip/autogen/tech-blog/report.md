# Roundtrip — autogen/tech-blog

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/autogen/tech-blog/source_files`
- target framework: `autogen`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=0.958 R=0.958 F1=0.958
- **property**: P=1.000 R=0.962 F1=0.980
- **triple**: P=0.770 R=0.762 F1=0.766
- **literal_overlap**: 0.923

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 20
- avg score: 0.983

## AST diff (source vs generated)
- overall: P=1.0 R=0.978 F1=0.989
  - decorators: ref=0 cand=0 F1=1.0
  - functions: ref=1 cand=1 F1=1.0
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=0 cand=0 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - state_annotations: ref=0 cand=0 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=5 cand=4 F1=0.889
  - classes: ref=0 cand=0 F1=1.0

## Execution trace
- skipped
