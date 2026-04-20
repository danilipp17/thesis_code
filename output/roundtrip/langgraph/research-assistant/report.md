# Roundtrip — langgraph/research-assistant

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/research-assistant/source_files`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/research-assistant`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/research-assistant/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/research-assistant/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/research-assistant/ttl2.ttl

## TTL₁ vs TTL₂ (ontology round-trip)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.787 R=0.787 F1=0.787
- **literal_overlap**: 0.744

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 22
- avg score: 0.99

## AST diff (source vs generated)
- overall: P=0.563 R=0.6 F1=0.581
  - decorators: ref=1 cand=1 F1=1.0
  - functions: ref=5 cand=5 F1=0.4
  - decorator_args: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_fields: ref=3 cand=3 F1=1.0
  - state_annotations: ref=3 cand=3 F1=1.0
  - graph_calls: ref=5 cand=7 F1=0.0
  - imports: ref=4 cand=6 F1=0.8
  - classes: ref=1 cand=1 F1=0.0

## Execution trace
- skipped
