# Roundtrip — crewai/email-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/email-flow/source_files`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/email-flow`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/email-flow/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/email-flow/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/email-flow/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.882 R=0.882 F1=0.882
- **literal_overlap**: 0.926

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 29
- avg score: 0.989
  - AgenticSystem: 1 matched, avg=0.667
  - EndStep: 2 matched, avg=1.0
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 6 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 3 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - Tool: 4 matched, avg=1.0
  - WorkflowStep: 3 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.781 R=0.761 F1=0.771
  - classes: ref=4 cand=5 F1=0.444
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=10 cand=9 F1=0.632
  - decorator_args: ref=2 cand=1 F1=0.667
  - decorators: ref=6 cand=6 F1=0.833
  - state_fields: ref=2 cand=2 F1=1.0
  - class_bases: ref=4 cand=5 F1=0.444
  - state_annotations: ref=2 cand=2 F1=1.0
  - functions: ref=12 cand=15 F1=0.815

## Execution trace
- skipped

