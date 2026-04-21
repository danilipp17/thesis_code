# Roundtrip — langgraph/drafter

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/langgraph/drafter`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/roundtrip/langgraph/drafter/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=0.900 R=1.000 F1=0.947
- **property**: P=0.941 R=0.970 F1=0.955
- **triple**: P=0.647 R=0.688 F1=0.667
- **literal_overlap**: 0.731
- missing properties (1): hasDecoratorArgument
- extra properties (2): hasAgentGoal, useLanguageModel

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 14
- avg score: 0.97
  - AgenticSystem: 1 matched, avg=0.583
  - EndStep: 2 matched, avg=1.0
  - LLMAgent: 1 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 2 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 1 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - Tool: 2 matched, avg=1.0
  - WorkflowStep: 1 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.667 R=0.637 F1=0.652
  - classes: ref=1 cand=1 F1=0.0
  - graph_calls: ref=5 cand=4 F1=0.444
  - imports: ref=5 cand=6 F1=0.909
  - decorator_args: ref=0 cand=0 F1=1.0
  - decorators: ref=1 cand=1 F1=1.0
  - state_fields: ref=1 cand=1 F1=1.0
  - class_bases: ref=1 cand=1 F1=0.0
  - state_annotations: ref=1 cand=1 F1=1.0
  - functions: ref=6 cand=3 F1=0.444

## Execution trace
- skipped

