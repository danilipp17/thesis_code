# Generation — autogen/custom_system

- source: `C:\Users\Dani\Thesis\Extractor\evaluation\fixtures\custom_system.ttl`
- work dir: `C:\Users\Dani\Thesis\Extractor\output\gui\generation\autogen\custom_system`

## Pipeline
- `generate` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\generation\autogen\custom_system\generated
- `reextract` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\generation\autogen\custom_system\reextracted.ttl

## Intrinsic metrics (single TTL)
- source: `C:\Users\Dani\Thesis\Extractor\evaluation\fixtures\custom_system.ttl`
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
- **individual**: P=1.000 R=0.846 F1=0.917
- **property**: P=1.000 R=0.800 F1=0.889
- **triple**: P=0.056 R=0.042 F1=0.048
- **literal_overlap**: 0.361
- missing properties (7): dependsOn, hasAssociatedTask, hasDependencyType, hasExpectedOutput, nextStep, performedByAgent, promptOutputIndicator

