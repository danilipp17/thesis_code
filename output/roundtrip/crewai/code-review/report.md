# Roundtrip — crewai/code-review

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/code-review/source_files`
- target framework: `crewai`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/code-review`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/code-review/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/code-review/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/code-review/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=0.977 F1=0.989
- **triple**: P=0.876 R=0.867 F1=0.871
- **literal_overlap**: 0.929

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 33
- avg score: 0.991

## AST diff (source vs generated)
- overall: P=0.884 R=0.863 F1=0.873
  - decorators: ref=8 cand=8 F1=0.875
  - functions: ref=14 cand=14 F1=1.0
  - decorator_args: ref=3 cand=3 F1=1.0
  - class_bases: ref=6 cand=6 F1=0.667
  - state_fields: ref=9 cand=9 F1=1.0
  - state_annotations: ref=9 cand=9 F1=0.889
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=9 cand=7 F1=0.75
  - classes: ref=6 cand=6 F1=0.667

## Execution trace
- skipped
