# Roundtrip — crewai/content-pipeline

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/content-pipeline/source_files`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/content-pipeline/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.869 R=0.869 F1=0.869
- **literal_overlap**: 0.920

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 27
- avg score: 0.991
  - AgenticSystem: 1 matched, avg=0.762
  - EndStep: 2 matched, avg=1.0
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 6 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 3 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - Tool: 2 matched, avg=1.0
  - WorkflowStep: 3 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.905 R=0.868 F1=0.886
  - classes: ref=7 cand=7 F1=0.571
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=9 cand=6 F1=0.8
  - decorator_args: ref=0 cand=0 F1=1.0
  - decorators: ref=5 cand=5 F1=1.0
  - state_fields: ref=6 cand=6 F1=1.0
  - class_bases: ref=7 cand=7 F1=0.571
  - state_annotations: ref=6 cand=6 F1=1.0
  - functions: ref=11 cand=11 F1=1.0

## Execution trace
- skipped

