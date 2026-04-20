# Roundtrip — autogen/comprehensive

- source: `/Users/danilippmann/Documents/Work/thesis_code/examples/autogen/comprehensive`
- work dir: `/Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/autogen/comprehensive`

## Pipeline
- `extract_1` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/autogen/comprehensive/ttl1.ttl
- `generate` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/autogen/comprehensive/generated
- `extract_2` ✓ /Users/danilippmann/Documents/Work/thesis_code/output/gui/roundtrip/autogen/comprehensive/ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=0.808 R=0.913 F1=0.857
- **property**: P=0.926 R=0.862 F1=0.893
- **triple**: P=0.532 R=0.563 F1=0.547
- **literal_overlap**: 0.710
- missing properties (4): hasCheckpointType, hasHumanCheckpoint, hasMaxTurns, isMandatory
- extra properties (2): hasDelegationStrategy, taskPrompt

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 14
- avg score: 0.963
  - AgenticSystem: 1 matched, avg=0.722
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=1.0
  - Prompt: 3 matched, avg=1.0
  - Team: 1 matched, avg=0.762
  - Tool: 2 matched, avg=1.0

## AST diff (source vs generated)
- overall: P=0.852 R=0.889 F1=0.87
  - class_bases: ref=0 cand=0 F1=1.0
  - classes: ref=0 cand=0 F1=1.0
  - functions: ref=2 cand=3 F1=0.8
  - state_annotations: ref=0 cand=0 F1=1.0
  - graph_calls: ref=0 cand=0 F1=1.0
  - imports: ref=1 cand=6 F1=0.0
  - decorators: ref=0 cand=0 F1=1.0
  - state_fields: ref=0 cand=0 F1=1.0
  - decorator_args: ref=0 cand=0 F1=1.0

## Execution trace
- skipped

