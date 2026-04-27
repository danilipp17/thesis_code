---
name: Gold A-Box annotation guideline
description: Rules governing how a Python source file is hand-annotated into an AgentOscin A-Box, used to construct the gold reference for extraction evaluation
---

# Gold A-Box annotation guideline (v1)

This guideline tells the (single) annotator how to read a framework source
file and produce a gold A-Box in the AgentOscin ontology. The goal is
*intra-annotator-stable* annotation: re-annotating the same system after a
delay should yield A-Boxes whose pairwise F1 ≥ 0.90 at the individual level.
The thesis reports this self-consistency number as the lower bound on gold
reliability, with the explicit caveat that it does not control for the
annotator's own systematic biases.

The guideline is intentionally restrictive. A construct is annotated only if
the rules below say so; "feels like an X" is not enough. The restrictive
rules + self-consistency check are how a single annotator approximates the
discipline that two annotators would have provided.

## 1. Scope

Annotate only what is *declared in source* and *reachable from a top-level
entry point* (`if __name__ == "__main__"`, `kickoff()`, exported `app`,
notebook cell with no guarding `if`). Library internals, dead code, commented
imports, and example strings inside docstrings are out of scope.

## 2. Naming and IRIs

- Use the instance namespace `http://oscin.example.org/<framework>/<system>#`.
- Local name = the source identifier (variable, decorator argument,
  YAML key) lowercased with non-alphanumerics replaced by `_`.
- If two source identifiers collide after normalization, suffix `_2`, `_3`.
- Anonymous individuals (LLM-instantiated tools, inline lambdas) get a
  stable name `<role>_<index>` reading top-to-bottom.

## 3. Class assignment rules

### 3.1 `:Agent` (or subclass `:LLMAgent` / `:HumanAgent`)

Annotate as `:LLMAgent`:

- **CrewAI**: every method decorated `@agent` returning an `Agent(...)`; every
  member of a `Crew(agents=[...])` list; every `assistant=` argument to a
  `Flow` step.
- **LangGraph**: every binding of the form `<name> = create_react_agent(...)`;
  every `<name> = ChatOpenAI(...)` *that is later passed to* a node function
  as the model. A bare `ChatOpenAI` not used as a node's model is **not** an
  agent (it is `:LLMConfig`).
- **AutoGen**: every instantiation of `AssistantAgent(...)`,
  `OpenAIAssistantAgent(...)`, `SocietyOfMindAgent(...)`.

Annotate as `:HumanAgent`:

- **AutoGen**: every `UserProxyAgent(...)` (regardless of `human_input_mode`).
- **CrewAI**: any `@agent` with `human_input=True`.
- **LangGraph**: not annotated as a separate agent — HITL is captured via
  `:hasHumanInteraction true` on the surrounding step (see §3.5).

### 3.2 `:Tool`

Every callable that is *registered as a tool*, identified by:

- `@tool` decorator (LangChain/LangGraph),
- entry in a `tools=[...]` list passed to an Agent constructor,
- subclass of `BaseTool` or `crewai.tools.BaseTool`.

A plain helper function used inside an agent's body is **not** a tool.

### 3.3 `:Prompt`

Every string literal or YAML field that is *passed to* an LLM as the
system/user prompt. Specifically:

- CrewAI YAML keys `role`, `goal`, `backstory` → one `:Prompt` per agent
  (joined). Task YAML `description`/`expected_output` → one `:Prompt` per
  task.
- LangGraph: `state_modifier=`, `prompt=`, or the system message in
  `[SystemMessage(content=...)]`.
- AutoGen: `system_message=` argument.

A prompt template stored only as a Python f-string with no LLM call is **not**
a prompt.

### 3.4 `:WorkflowStep` / `:Task`

- **CrewAI**: each `@task` method → one `:Task`; each `@start`/`@listen`/
  `@router` method → one `:WorkflowStep`.
- **LangGraph**: each `graph.add_node("X", fn)` → one `:WorkflowStep` named `X`.
- **AutoGen**: there are no explicit workflow steps; do **not** invent them.
  Coordination is captured at team level (§3.6).

### 3.5 Step-level properties

On each step, annotate when literally present in source:

- `:hasHumanInteraction true` if the step body calls `interrupt(...)` or
  reads `input(...)` from stdin.
- `:hasGuardrail` if a `guardrail=` argument or `@validator`/Pydantic
  validation is attached.
- `:invokesAgent <agent>` if exactly one agent is called inside the step.
- `:invokesTool <tool>` for each tool call inside the step.

### 3.6 `:Team` and coordination

- One `:Team` per `Crew(...)`, per `StateGraph`, per `GroupChat(...)` or
  `RoundRobinGroupChat(...)`.
- `:hasCoordinationPattern`:
  - `"sequential"` for `Process.sequential`, linear chain in a StateGraph,
    or AutoGen `RoundRobin`.
  - `"hierarchical"` for `Process.hierarchical` or AutoGen `Selector`.
  - `"reactive"` for any team whose only routing is conditional edges.
  Do **not** invent a pattern; if none of these applies, omit the property.

### 3.7 `:Goal` / `:Objective`

- Annotate `:Goal` only when source provides a literal team-level goal —
  CrewAI `Crew(goal=...)`, an explicit `team_goal` field. Do **not**
  synthesize from the README.
- Annotate `:Objective` only for explicit per-agent / per-task objectives.

### 3.8 `:Memory`

- `:Memory` if and only if `memory=True` (CrewAI) or a checkpointer /
  `MemorySaver` is wired to the graph (LangGraph) or `model_context=` is
  set (AutoGen ≥ 0.4).

### 3.9 Reasoning

- `:hasReasoningPattern "ReAct"` if the agent is created by
  `create_react_agent` or its system prompt contains a literal
  Thought/Action/Observation scaffold.
- `:reasoning true` only when `reasoning=True` is passed.
- Do **not** infer reasoning from "the agent uses tools".

## 4. What NOT to annotate

- Logging, retries, rate limiting, observability decorators.
- `print` statements, debug branches.
- Tests, fixtures, mock objects.
- Imports of unused symbols.

## 5. Self-consistency protocol (single annotator)

Because there is no second annotator, the gold is checked by *re-annotation
after a delay*. Procedure:

1. **Pass A.** Annotate all six systems following §3 strictly. Save as
   `gold/<framework>/<system>/passA.ttl`. Track every "I'm not sure" call in
   the open-issues log (§6) as you go.
2. **Cool-down.** Wait at least 7 days. Do not look at pass A.
3. **Pass B.** Re-annotate the same six systems blind to pass A
   (`gold/.../passB.ttl`).
4. **Compute self-F1.** Pairwise individual / property / triple F1 between
   pass A and pass B per system. Report mean ± std in the thesis as gold
   reliability.
5. **Reconcile.** Where A and B disagree:
   - Rule cited in §3 wins. If the rule is silent, exclude the disputed
     individual from gold and add the case to §6.
   - Class disagreement (`Agent` vs `Tool`): use the §3.2 / §3.3
     creation-site rule.
   - Property disagreement: keep the property only if A and B agree.
     Conservative — deflates recall slightly but keeps gold trustworthy.
6. The reconciled file is `gold/<framework>/<system>/gold.ttl` and is the
   reference used for all extraction metrics.

## 6. Open issues log

Track cases the rules don't resolve here. Each entry: system, construct, the
candidate interpretations, and the chosen resolution (or "excluded"). The log
is appended (not edited) so the audit trail survives. The thesis cites the
log size as a measure of how often the guideline ran out.

## 7. Versioning

Bump `v1 → v2` when a rule changes; re-annotate all six systems and report
the F1 delta in the thesis.
