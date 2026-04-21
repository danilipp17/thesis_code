# Roundtrip — autogen/content-pipeline

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/autogen/content-pipeline/source_files`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/content-pipeline`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/content-pipeline/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/content-pipeline/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/content-pipeline/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=0.963 F1=0.981
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.807 R=0.793 F1=0.800
- **literal_overlap**: 0.971

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 22
- avg score: 0.989
  - AgenticSystem: 1 matched, avg=0.762
  - EndStep: 2 matched, avg=1.0
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 4 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 1 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - Tool: 2 matched, avg=1.0
  - WorkflowStep: 2 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=1.0 R=0.972 F1=0.986
  - classes: ref=0 cand=0 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=8 cand=6 F1=0.857
  - decorator_args: ref=0 cand=0 F1=1.0
  - decorators: ref=0 cand=0 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - class_bases: ref=0 cand=0 F1=1.0
  - state_annotations: ref=0 cand=0 F1=1.0
  - functions: ref=3 cand=3 F1=1.0

## Execution trace
- skipped

