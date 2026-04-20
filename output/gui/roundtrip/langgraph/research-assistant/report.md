# Roundtrip — langgraph/research-assistant

- source: `C:\Users\Dani\Thesis\Extractor\examples\langgraph\research-assistant\source_files`
- work dir: `C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\langgraph\research-assistant`

## Pipeline
- `extract_1` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\langgraph\research-assistant\ttl1.ttl
- `generate` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\langgraph\research-assistant\generated
- `extract_2` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\langgraph\research-assistant\ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=1.000 R=1.000 F1=1.000
- **property**: P=1.000 R=1.000 F1=1.000
- **triple**: P=0.787 R=0.787 F1=0.787
- **literal_overlap**: 0.744

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 22
- avg score: 0.99
  - AgenticSystem: 1 matched, avg=0.783
  - ConditionalStep: 1 matched, avg=1.0
  - EndStep: 2 matched, avg=1.0
  - Goal: 2 matched, avg=1.0
  - LLMAgent: 2 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 4 matched, avg=1.0
  - StartStep: 2 matched, avg=1.0
  - Task: 2 matched, avg=1.0
  - Team: 1 matched, avg=1.0
  - Tool: 2 matched, avg=1.0
  - WorkflowStep: 2 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.563 R=0.6 F1=0.581
  - imports: ref=4 cand=6 F1=0.8
  - state_annotations: ref=3 cand=3 F1=1.0
  - functions: ref=5 cand=5 F1=0.4
  - decorators: ref=1 cand=1 F1=1.0
  - classes: ref=1 cand=1 F1=0.0
  - state_fields: ref=3 cand=3 F1=1.0
  - graph_calls: ref=5 cand=7 F1=0.0
  - class_bases: ref=1 cand=1 F1=0.0
  - decorator_args: ref=0 cand=0 F1=1.0

## Execution trace
- skipped

