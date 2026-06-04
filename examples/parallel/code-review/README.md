# code-review

**Origin:** AutoGen. **Scenario:** multi-agent code review of a small
hardcoded snippet (a `process_user_input` function that calls `eval(data)`).

Three agents collaborate:

1. **Code_Reviewer** — checks correctness, readability, naming, code smells.
2. **Security_Auditor** — audits for OWASP Top 10 / CWE-classified findings.
3. **Review_Summarizer** — synthesises a structured report with a verdict.

The first two share a custom **`code_analyzer`** tool (a Python AST-based
static analyzer); the summariser does not.

## Framework variants

| variant   | source                                                   | flavour                                                                  |
|-----------|----------------------------------------------------------|--------------------------------------------------------------------------|
| autogen   | `examples/autogen/code-review/source_files`              | `RoundRobinGroupChat([reviewer, auditor, summarizer], max_turns=3)`; tool wrapped as `FunctionTool` and attached to reviewer + auditor |
| crewai    | `examples/parallel/code-review/crewai/source_files`      | `CodeReviewFlow(Flow[CodeReviewState])` wrapping a `@CrewBase CodeReviewCrew` with three YAML-configured agents/tasks (`context=[…]` edges); tool registered via `@tool("Code Analyzer")` and shared by the reviewer and auditor |
| langgraph | `examples/parallel/code-review/langgraph/source_files`   | linear `StateGraph` over three node functions; `code_analyzer` is a plain Python helper called inside the reviewer / auditor nodes, whose output is fed back to the LLM as part of the prompt (no tool-calling roundtrip) |

The tool-binding model differs across the three frameworks (FunctionTool +
LLM tool-calling in AutoGen, decorator-based registered tool in CrewAI,
direct helper call in LangGraph) — itself a finding. Equivalence is by
inspection only.
