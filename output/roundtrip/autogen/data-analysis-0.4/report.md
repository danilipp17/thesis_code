# Roundtrip — autogen/data-analysis-0.4

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/autogen/data-analysis-0.4/source_files`
- target framework: `autogen`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/data-analysis-0.4`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/data-analysis-0.4/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/data-analysis-0.4/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/data-analysis-0.4/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=0.963 F1=0.981
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.782 R=0.768 F1=0.775
- **literal_overlap**: 0.875

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 22
- avg score: 0.991

## AST diff (source vs generated)
- overall: P=0.963 R=0.978 F1=0.97
  - decorators: ref=0 cand=0 F1=1.0
  - functions: ref=3 cand=3 F1=1.0
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=0 cand=0 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - state_annotations: ref=0 cand=0 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=5 cand=6 F1=0.727
  - classes: ref=0 cand=0 F1=1.0

## Execution trace
- skipped
