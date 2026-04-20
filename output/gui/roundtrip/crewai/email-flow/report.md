# Roundtrip — crewai/email-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/crewai/email-flow/source_files`
- target framework: `langgraph`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/email-flow`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/email-flow/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/email-flow/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/crewai/email-flow/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=0.964 R=0.692 F1=0.806
- **property**: P=1.000 R=0.795 F1=0.886
- **triple**: P=0.109 R=0.075 F1=0.089
- **literal_overlap**: 0.278
- missing properties (9): agentToolUsage, configKey, configValue, hasAgentConfig, hasDecoratorArgument, hasReference, hasSystemConfig, orchestratesTeam, promptContext

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 19
- avg score: 0.803
  - AgenticSystem: 1 matched, avg=0.667
  - EndStep: 2 matched, avg=0.875
  - Goal: 1 matched, avg=0.582
  - LLMAgent: 1 matched, avg=0.596
  - Orchestration: 1 matched, avg=0.567
  - Prompt: 4 matched, avg=0.685
  - StartStep: 1 matched, avg=1.0
  - Task: 2 matched, avg=0.681
  - Tool: 4 matched, avg=1.0
  - WorkflowStep: 2 matched, avg=1.0

## Mapping conformance (CrewAI Flow ↔ LangGraph)
- direction: cf_to_lg
- overall: 0.75
- applicable rules: 6
  - graph_class: lg=1 cf=1 score=1.0
  - node_to_decorated: lg=3 cf=2 score=0.667
  - entry_point: lg=1 cf=1 score=1.0
  - sequential_edge: lg=1 cf=1 score=1.0
  - conditional: lg=0 cf=0 score=None
  - state_reducer: lg=1 cf=2 score=0.5
  - kickoff: lg=1 cf=3 score=0.333

