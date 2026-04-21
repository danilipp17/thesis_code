# Roundtrip — langgraph/memoryagent

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/memoryagent`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/memoryagent/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=0.933 R=1.000 F1=0.966
- **triple**: P=0.722 R=0.743 F1=0.732
- **literal_overlap**: 0.889
- extra properties (2): hasExpectedOutput, promptOutputIndicator

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 13
- avg score: 0.976
  - AgenticSystem: 1 matched, avg=0.688
  - EndStep: 2 matched, avg=1.0
  - Goal: 1 matched, avg=1.0
  - LLMAgent: 1 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 2 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 1 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - WorkflowStep: 1 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.778 R=0.704 F1=0.739
  - classes: ref=1 cand=1 F1=0.0
  - graph_calls: ref=3 cand=2 F1=0.8
  - imports: ref=6 cand=4 F1=0.8
  - decorator_args: ref=0 cand=0 F1=1.0
  - decorators: ref=0 cand=0 F1=1.0
  - state_fields: ref=1 cand=1 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_annotations: ref=1 cand=1 F1=1.0
  - functions: ref=1 cand=1 F1=1.0

## Execution trace
- skipped

