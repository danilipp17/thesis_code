# Generation — langgraph/custom_system

- source: `/Users/danilippmann/Documents/Work/thesis_code/evaluation/fixtures/custom_system.ttl`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/langgraph/custom_system`

## Pipeline
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/langgraph/custom_system/generated
- `reextract` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/langgraph/custom_system/reextracted.ttl

## Intrinsic metrics (single TTL)
- source: `/Users/danilippmann/Documents/Work/thesis_code/evaluation/fixtures/custom_system.ttl`
- total triples: 601
- ABox triples: 118
- individuals: 26
- properties used: 35
- information density: 4.538 triples/indiv
- literals / object-links: 48 / 65
- individuals by class:
  - AgenticSystem: 1
  - EndStep: 3
  - Goal: 2
  - LLMAgent: 2
  - LanguageModel: 1
  - Orchestration: 1
  - Prompt: 4
  - StartStep: 2
  - Task: 2
  - TaskCompletionTermination: 1
  - Team: 1
  - Tool: 1
  - WorkflowPattern: 2
  - WorkflowStep: 3

## Syntax validity (generated source)
- files checked: 2
- syntax ok rate: 1.0 (2/2)
- import resolution rate: 1.0

## TTL pairwise (reference vs candidate)
- **individual**: P=0.758 R=0.962 F1=0.847
- **property**: P=0.943 R=0.943 F1=0.943
- **triple**: P=0.112 R=0.144 F1=0.126
- **literal_overlap**: 0.389
- missing properties (2): agentToolUsage, promptContext
- extra properties (2): hasOutputSchema, hasSchemaDefinition

