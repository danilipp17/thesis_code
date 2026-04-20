# Generation — autogen/email-flow

- source: `/Users/danilippmann/Documents/Work/thesis_code/output/extraction/crewai/email-flow/extracted.ttl`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/autogen/email-flow`

## Pipeline
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/autogen/email-flow/generated
- `reextract` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/generation/autogen/email-flow/reextracted.ttl

## Intrinsic metrics (single TTL)
- source: `/Users/danilippmann/Documents/Work/thesis_code/output/extraction/crewai/email-flow/extracted.ttl`
- total triples: 670
- ABox triples: 187
- individuals: 39
- properties used: 44
- information density: 4.795 triples/indiv
- literals / object-links: 82 / 100
- individuals by class:
  - AgenticSystem: 1
  - Config: 5
  - EndStep: 2
  - Goal: 3
  - LLMAgent: 3
  - LanguageModel: 1
  - Orchestration: 1
  - Prompt: 6
  - Schema: 1
  - StartStep: 2
  - Task: 3
  - TaskCompletionTermination: 1
  - Team: 1
  - Tool: 4
  - WorkflowPattern: 2
  - WorkflowStep: 3

## Syntax validity (generated source)
- files checked: 2
- syntax ok rate: 1.0 (2/2)
- import resolution rate: 1.0

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=0.718 F1=0.836
- **property**: P=1.000 R=0.636 F1=0.778
- **triple**: P=0.032 R=0.021 F1=0.026
- **literal_overlap**: 0.333
- missing properties (16): configKey, configValue, dependsOn, hasAgentConfig, hasAssociatedTask, hasDecoratorArgument, hasDependencyType, hasExpectedOutput, hasOutputSchema, hasReference…

