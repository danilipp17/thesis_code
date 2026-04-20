# Roundtrip — crewai/self-eval-loop-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/self-eval-loop-flow/source_files`
- target framework: `crewai`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/self-eval-loop-flow`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/self-eval-loop-flow/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/self-eval-loop-flow/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/self-eval-loop-flow/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.860 R=0.854 F1=0.857
- **literal_overlap**: 0.957

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 28
- avg score: 0.993

## AST diff (source vs generated)
- overall: P=0.921 R=0.927 F1=0.924
  - decorators: ref=7 cand=7 F1=0.857
  - functions: ref=12 cand=11 F1=0.957
  - decorator_args: ref=3 cand=3 F1=1.0
  - class_bases: ref=7 cand=7 F1=0.857
  - state_fields: ref=6 cand=6 F1=1.0
  - state_annotations: ref=6 cand=7 F1=0.923
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=7 cand=7 F1=0.857
  - classes: ref=7 cand=7 F1=0.857

## Execution trace
- skipped
