# Generation — crewai/extracted

- source: `/Users/danilippmann/Documents/Work/thesis_code/output/extraction/crewai/email-flow/extracted.ttl`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/generation/crewai/extracted`

## Pipeline
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/generation/crewai/extracted/generated

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
- files checked: 3
- syntax ok rate: 1.0 (3/3)
- import resolution rate: 0.333
- files with unresolved imports (2):
  - `/Users/danilippmann/Documents/Work/thesis_code/output/generation/crewai/extracted/generated/crews/email_filter_crew/email_filter_crew.py`: crewai_tools, langchain_community, langchain_community, tools
  - `/Users/danilippmann/Documents/Work/thesis_code/output/generation/crewai/extracted/generated/main.py`: crews

## AST diff (source vs generated)
- overall: P=0.829 R=0.752 F1=0.789
  - imports: ref=10 cand=8 F1=0.667
  - classes: ref=4 cand=5 F1=0.444
  - state_annotations: ref=2 cand=2 F1=1.0
  - state_fields: ref=2 cand=2 F1=1.0
  - decorator_args: ref=2 cand=1 F1=0.667
  - functions: ref=12 cand=11 F1=0.87
  - graph_calls: ref=0 cand=0 F1=1.0
  - class_bases: ref=4 cand=5 F1=0.444
  - decorators: ref=6 cand=5 F1=0.909

