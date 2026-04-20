# Roundtrip — crewai/academic-research-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/academic-research-flow/source_files`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/academic-research-flow`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/academic-research-flow/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/academic-research-flow/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/academic-research-flow/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=0.977 R=0.956 F1=0.966
- **property**: P=1.000 R=0.926 F1=0.962
- **triple**: P=0.838 R=0.824 F1=0.831
- **literal_overlap**: 0.873
- missing properties (4): dependsOn, hasDependencyType, hasTeamMemoryBinding, orchestratesTeam

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 27
- avg score: 0.993
  - AgenticSystem: 1 matched, avg=0.815
  - ConditionalStep: 1 matched, avg=1.0
  - EndStep: 4 matched, avg=1.0
  - Goal: 2 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 4 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 2 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - Tool: 1 matched, avg=1.0
  - WorkflowStep: 5 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.746 R=0.739 F1=0.742
  - class_bases: ref=7 cand=7 F1=0.714
  - classes: ref=7 cand=7 F1=0.714
  - functions: ref=11 cand=13 F1=0.917
  - state_annotations: ref=11 cand=11 F1=0.727
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=8 cand=7 F1=0.933
  - decorators: ref=8 cand=7 F1=0.667
  - state_fields: ref=11 cand=11 F1=1.0
  - decorator_args: ref=2 cand=0 F1=0.0

## Execution trace
- skipped

