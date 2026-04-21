# Roundtrip — crewai/tech-blog

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/tech-blog/source_files`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/tech-blog`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/tech-blog/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/tech-blog/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/crewai/tech-blog/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.864 R=0.864 F1=0.864
- **literal_overlap**: 0.973

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 20
- avg score: 0.983
  - AgenticSystem: 1 matched, avg=0.667
  - EndStep: 1 matched, avg=1.0
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Prompt: 6 matched, avg=1.0
  - StartStep: 1 matched, avg=1.0
  - Task: 3 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - WorkflowStep: 1 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.986 R=0.958 F1=0.972
  - classes: ref=1 cand=1 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=4 cand=3 F1=0.857
  - decorator_args: ref=0 cand=0 F1=1.0
  - decorators: ref=3 cand=3 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - class_bases: ref=1 cand=1 F1=1.0
  - state_annotations: ref=0 cand=0 F1=1.0
  - functions: ref=8 cand=8 F1=0.875

## Execution trace
- skipped

