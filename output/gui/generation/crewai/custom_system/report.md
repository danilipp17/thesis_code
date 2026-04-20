# Generation — crewai/custom_system

- source: `/Users/danilippmann/Documents/Work/thesis_code/evaluation/fixtures/custom_system.ttl`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/crewai/custom_system`

## Pipeline
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/crewai/custom_system/generated
- `reextract` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/crewai/custom_system/reextracted.ttl

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
- files checked: 3
- syntax ok rate: 1.0 (3/3)
- import resolution rate: 0.667
- files with unresolved imports (1):
  - `/Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/crewai/custom_system/generated/crews/editorial_team/editorial_team.py`: tools

## TTL pairwise (reference vs candidate)
- **individual**: P=0.963 R=1.000 F1=0.981
- **property**: P=0.946 R=1.000 F1=0.972
- **triple**: P=0.795 R=0.822 F1=0.808
- **literal_overlap**: 0.889
- extra properties (2): hasOutputSchema, hasSchemaDefinition

