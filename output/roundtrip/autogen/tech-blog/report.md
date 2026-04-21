# Roundtrip — autogen/tech-blog

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/autogen/tech-blog/source_files`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/autogen/tech-blog/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.792 R=0.792 F1=0.792
- **literal_overlap**: 0.962

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 20
- avg score: 0.983
  - AgenticSystem: 1 matched, avg=0.667
  - EndStep: 2 matched, avg=1.0
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 4 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 1 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - WorkflowStep: 2 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=1.0 R=0.978 F1=0.989
  - classes: ref=0 cand=0 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=5 cand=4 F1=0.889
  - decorator_args: ref=0 cand=0 F1=1.0
  - decorators: ref=0 cand=0 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - class_bases: ref=0 cand=0 F1=1.0
  - state_annotations: ref=0 cand=0 F1=1.0
  - functions: ref=1 cand=1 F1=1.0

## Execution trace
- skipped

