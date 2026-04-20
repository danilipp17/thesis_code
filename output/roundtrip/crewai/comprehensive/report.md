# Roundtrip — crewai/comprehensive

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/comprehensive/source_files`
- target framework: `crewai`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/comprehensive`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/comprehensive/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/comprehensive/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/comprehensive/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=0.905 F1=0.950
- **property**: P=0.959 R=0.839 F1=0.895
- **triple**: P=0.850 R=0.782 F1=0.814
- **literal_overlap**: 0.818

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 26
- avg score: 0.989

## AST diff (source vs generated)
- overall: P=0.78 R=0.808 F1=0.794
  - decorators: ref=8 cand=7 F1=0.8
  - functions: ref=11 cand=11 F1=0.909
  - decorator_args: ref=3 cand=2 F1=0.8
  - class_bases: ref=5 cand=8 F1=0.615
  - state_fields: ref=4 cand=4 F1=1.0
  - state_annotations: ref=4 cand=4 F1=0.75
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=5 cand=6 F1=0.545
  - classes: ref=5 cand=8 F1=0.615

## Execution trace
- skipped
