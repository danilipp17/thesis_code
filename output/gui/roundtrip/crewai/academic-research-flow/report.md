# Roundtrip — crewai/academic-research-flow

- source: `C:\Users\Dani\Thesis\Extractor\examples\crewai\academic-research-flow\source_files`
- target framework: `langgraph`
- work dir: `C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\academic-research-flow`

## Pipeline
- `extract_1` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\academic-research-flow\ttl1.ttl
- `generate` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\academic-research-flow\generated
- `extract_2` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\academic-research-flow\ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=0.633 R=0.689 F1=0.660
- **property**: P=0.946 R=0.648 F1=0.769
- **triple**: P=0.112 R=0.138 F1=0.124
- **literal_overlap**: 0.291
- missing properties (19): agentToolUsage, bindsMemory, configKey, configValue, employsReasoningPattern, hasAgentConfig, hasCheckpointPosition, hasCheckpointType, hasHumanCheckpoint, hasMaxReasoningAttempts…
- extra properties (2): hasEdgeMapping, performedByAgent

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 20
- avg score: 0.863
  - AgenticSystem: 1 matched, avg=0.815
  - ConditionalStep: 1 matched, avg=1.0
  - EndStep: 3 matched, avg=1.0
  - Goal: 1 matched, avg=0.78
  - LLMAgent: 3 matched, avg=0.641
  - Orchestration: 1 matched, avg=0.586
  - Prompt: 3 matched, avg=0.715
  - StartStep: 1 matched, avg=1.0
  - Tool: 1 matched, avg=1.0
  - WorkflowStep: 5 matched, avg=1.0

## Mapping conformance (CrewAI Flow ↔ LangGraph)
- direction: cf_to_lg
- overall: 0.775
- applicable rules: 7
  - graph_class: lg=1 cf=1 score=1.0
  - node_to_decorated: lg=6 cf=5 score=0.833
  - entry_point: lg=1 cf=1 score=1.0
  - sequential_edge: lg=3 cf=3 score=1.0
  - conditional: lg=1 cf=1 score=1.0
  - state_reducer: lg=1 cf=11 score=0.091
  - kickoff: lg=1 cf=2 score=0.5

