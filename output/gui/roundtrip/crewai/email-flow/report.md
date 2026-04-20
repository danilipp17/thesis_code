# Roundtrip — crewai/email-flow

- source: `C:\Users\Dani\Thesis\Extractor\examples\crewai\email-flow\source_files`
- target framework: `autogen`
- work dir: `C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\email-flow`

## Pipeline
- `extract_1` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\email-flow\ttl1.ttl
- `generate` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\email-flow\generated
- `extract_2` ✓ C:\Users\Dani\Thesis\Extractor\output\gui\roundtrip\crewai\email-flow\ttl2.ttl

## TTL pairwise (reference vs candidate)
- **individual**: P=0.800 R=0.718 F1=0.757
- **property**: P=1.000 R=0.636 F1=0.778
- **triple**: P=0.032 R=0.027 F1=0.029
- **literal_overlap**: 0.389
- missing properties (16): configKey, configValue, dependsOn, hasAgentConfig, hasAssociatedTask, hasDecoratorArgument, hasDependencyType, hasExpectedOutput, hasOutputSchema, hasReference…

## Fuzzy alignment (TTL₁ ↔ TTL₂)
- matched pairs: 17
- avg score: 0.899
  - AgenticSystem: 1 matched, avg=0.667
  - Goal: 3 matched, avg=1.0
  - LLMAgent: 3 matched, avg=1.0
  - Orchestration: 1 matched, avg=0.787
  - Prompt: 4 matched, avg=0.797
  - Task: 1 matched, avg=0.636
  - Tool: 4 matched, avg=1.0

