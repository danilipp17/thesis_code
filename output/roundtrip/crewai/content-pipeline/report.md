# Roundtrip — crewai/content-pipeline

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/content-pipeline/source_files`
- target framework: `crewai`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=0.976 F1=0.988
- **triple**: P=0.868 R=0.863 F1=0.865
- **literal_overlap**: 0.920

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 27
- avg score: 0.991

## AST diff (source vs generated)
- overall: P=0.905 R=0.868 F1=0.886
  - decorators: ref=5 cand=5 F1=1.0
  - functions: ref=11 cand=11 F1=1.0
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=7 cand=7 F1=0.571
  - state_fields: ref=6 cand=6 F1=1.0
  - state_annotations: ref=6 cand=6 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=9 cand=6 F1=0.8
  - classes: ref=7 cand=7 F1=0.571

## Execution trace
- skipped
