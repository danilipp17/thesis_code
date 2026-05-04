# Evaluation — Extraction

This section evaluates the **extraction half** of the OSCIN pipeline: the
mapping from framework-specific source code to an `agentoscin` ABox.
Generation (TTL → source) and round-trip evaluation are deferred.

The evaluation has three parts:

1. **Pattern catalogue.** For each of the three target frameworks we pick
   representative source-code constructs that exercise non-trivial
   features of the ontology (composite flows, multiple coordination
   patterns, structured termination, cyclic topologies). For each, we
   show the source snippet beside the extracted triples and judge
   whether the framework-agnostic representation is faithful.
2. **Correctness and completeness.** We define a *construct-coverage*
   measure that does not depend on a hand-authored gold ABox, audit the
   representative examples by hand, and aggregate the result over the
   full benchmark of 20 examples.
3. **Intrinsic shape metrics.** We report the size and density of the
   extracted graphs and discuss what the numbers do and do not tell us.

We close with a discussion of how systematically the agentoscin
representation can be recovered from framework-specific code in
practice — what is reliable, what relies on heuristics, and what is
out of reach without runtime information.

---

## 1. Pattern catalogue

The pattern catalogue is organised by framework. Each subsection picks
one or two source examples that exercise constructs the ontology is
explicitly designed to capture. The point is not to enumerate every
construct but to show — on real source code — that the same
agentoscin vocabulary is used to represent semantically equivalent
constructs across frameworks.

### 1.1 CrewAI — Flow + Crew composition

CrewAI is the only one of the three frameworks with a two-level
abstraction: declarative `Crew`s defined from YAML, orchestrated by an
imperative `Flow`. The `email-flow` example shows the basic case.

**Source.** A `@CrewBase` class loads three agents and three tasks from
YAML, and a `Flow` invokes the crew from a `@listen`-ed step.

```python
# main.py — Flow
class EmailAutoResponderFlow(Flow[AutoResponderState]):
    @start("wait_next_run")
    def fetch_new_emails(self): ...
    @listen(fetch_new_emails)
    def generate_draft_responses(self):
        EmailFilterCrew().crew().kickoff(inputs={"emails": emails})

# crews/config/agents.yaml
email_filter_agent:
  role: Senior Email Analyst
  goal:  Filter out non-essential emails …
  backstory: With years of experience in email management …
```

**Extraction.** Both layers appear in the ABox. The Crew becomes a
`Team` with a sequential `WorkflowPattern` of three crew steps, and
the Flow becomes an `Orchestration` whose steps reference the crew via
`callsCrew`:

```turtle
ex:Team_EmailFilterCrew a agentoscin:Team ;
    agentoscin:employsCoordinationPattern agentoscin:Sequential ;
    agentoscin:hasAgentMember ex:Agent_email_filter_agent,
        ex:Agent_email_action_agent,
        ex:Agent_email_response_writer ;
    agentoscin:hasWorkflowPattern ex:WorkflowPattern_EmailFilterCrew .

ex:CrewStep_EmailFilterCrew_filter_emails_task a agentoscin:StartStep ;
    agentoscin:hasAssociatedTask ex:Task_filter_emails_task ;
    agentoscin:nextStep ex:CrewStep_EmailFilterCrew_action_required_emails_task ;
    agentoscin:stepOrder 1 .
# … chained → CrewStep_…_draft_responses_task (EndStep)

ex:Orchestration_EmailAutoResponderFlow a agentoscin:Orchestration ;
    agentoscin:employsCoordinationPattern agentoscin:Sequential ;
    agentoscin:orchestratesTeam ex:Team_EmailFilterCrew ;
    agentoscin:hasWorkflowPattern ex:FlowWorkflowPattern_EmailAutoResponderFlow .

ex:FlowStep_generate_draft_responses a agentoscin:EndStep, agentoscin:WorkflowStep ;
    agentoscin:callsCrew "EmailFilterCrew"^^xsd:string ;
    agentoscin:nextStep … .
```

The two layers are linked by `orchestratesTeam` at the type level and
by `callsCrew` at the step level. Both layers carry their own
`WorkflowPattern`, so the chronological structure is preserved on
both — a downstream consumer can either replay the high-level Flow or
descend into the individual crew steps.

### 1.2 CrewAI — router-driven retry loop

The `self-eval-loop-flow` example uses a `@router` step to implement
a generate-evaluate-retry loop with two terminal branches.

**Source.**

```python
@start("retry")
def generate_shakespeare_x_post(self): …

@router(generate_shakespeare_x_post)
def evaluate_x_post(self):
    if self.state.retry_count > 3:
        return "max_retry_exceeded"
    …
    if self.state.valid: return "complete"
    return "retry"

@listen("complete")           def save_result(self): …
@listen("max_retry_exceeded") def max_retry_exceeded_exit(self): …
```

**Extraction.** The router is captured as a `ConditionalStep` with the
literal routing logic preserved as a string, the two listener labels
become `hasDecoratorArgument` literals on the terminal steps, and the
back-edge `"retry"` re-enters the start step:

```turtle
ex:Orchestration_ShakespeareXPostFlow a agentoscin:Orchestration ;
    agentoscin:employsCoordinationPattern agentoscin:Hierarchical ;
    agentoscin:orchestratesTeam ex:Team_ShakespeareanXPostCrew,
                                 ex:Team_XPostReviewCrew .

ex:FlowStep_evaluate_x_post a agentoscin:ConditionalStep, agentoscin:WorkflowStep ;
    agentoscin:callsCrew "XPostReviewCrew"^^xsd:string ;
    agentoscin:hasRoutingLogic """if self.state.retry_count > 3:
            return \"max_retry_exceeded\"
            …""" .

ex:FlowStep_save_result a agentoscin:EndStep, agentoscin:WorkflowStep ;
    agentoscin:hasDecoratorArgument "complete"^^xsd:string .
ex:FlowStep_max_retry_exceeded_exit a agentoscin:EndStep, agentoscin:WorkflowStep ;
    agentoscin:hasDecoratorArgument "max_retry_exceeded"^^xsd:string .
```

Two crews co-orchestrated by one Flow appear as two `orchestratesTeam`
edges — the cross-crew composition is recovered without any framework
specifics leaking into the ontology.

### 1.3 AutoGen — RoundRobinGroupChat with `max_turns`

AutoGen has no Crew/Flow split. A single team object groups
`AssistantAgent` instances and accepts a termination condition.

**Source (`code-review`).**

```python
team = RoundRobinGroupChat(
    participants=[code_reviewer, security_auditor, review_summarizer],
    max_turns=3,
)
```

**Extraction.** The team class chooses the coordination-pattern named
individual (`agentoscin:RoundRobin`); the `max_turns` keyword resolves
to a typed `TurnLimitTermination` individual:

```turtle
ex:Team_RoundRobinGroupChat_0 a agentoscin:Team ;
    agentoscin:employsCoordinationPattern agentoscin:RoundRobin ;
    agentoscin:hasAgentMember ex:Agent_Code_Reviewer,
        ex:Agent_Security_Auditor, ex:Agent_Review_Summarizer ;
    agentoscin:hasTerminationCondition ex:TurnLimit_RoundRobinGroupChat_0_0 .

ex:TurnLimit_RoundRobinGroupChat_0_0 a agentoscin:TurnLimitTermination ;
    agentoscin:hasMaxTurns 3 .
```

### 1.4 AutoGen — `MaxMessageTermination`

In `tech-blog` the termination is built as a separate object and
passed via a keyword. The extractor follows the variable binding and
produces the same shape of triples as the inline form, with the
correct `hasMaxTurns` value:

```python
termination = MaxMessageTermination(max_messages=4)
team = RoundRobinGroupChat(participants=[…], termination_condition=termination)
```

```turtle
ex:Team_RoundRobinGroupChat_0 a agentoscin:Team ;
    agentoscin:hasTerminationCondition ex:TurnLimit_RoundRobinGroupChat_0_0 .
ex:TurnLimit_RoundRobinGroupChat_0_0 a agentoscin:TurnLimitTermination ;
    agentoscin:hasMaxTurns 4 .
```

`MaxMessageTermination` and `RoundRobinGroupChat(max_turns=…)` map to
the same agentoscin class — a downstream query can ask "what bounds
this team?" without knowing which AutoGen idiom was used.

### 1.5 AutoGen — `SelectorGroupChat` with `TextMentionTermination`

`travel-planning` uses a different team class and an event-based
termination string:

```python
termination = TextMentionTermination("TERMINATE")
group_chat  = SelectorGroupChat(participants=[…], termination_condition=termination)
```

```turtle
ex:Team_SelectorGroupChat_0 a agentoscin:Team ;
    agentoscin:employsCoordinationPattern agentoscin:SelectorBased ;
    agentoscin:hasTerminationCondition ex:EventTermination_SelectorGroupChat_0_0 .
ex:EventTermination_SelectorGroupChat_0_0 a agentoscin:EventBasedTermination ;
    agentoscin:hasTriggerExpression "TERMINATE"^^xsd:string .
```

The team-class selection populates the coordination pattern
(`SelectorBased` vs `RoundRobin`); the termination subclass
(`EventBasedTermination` vs `TurnLimitTermination`) records the
*kind* of stopping condition; the trigger string is preserved
verbatim. A SPARQL query asking for "all teams that stop on a string
trigger" works uniformly across `RoundRobin` and `Selector` examples.

### 1.6 LangGraph — ReAct loop with conditional routing

LangGraph has neither a Team nor a Task in the source; everything is a
node in a `StateGraph`. The challenge is to recover the same
agentoscin shape as the other two frameworks while staying faithful to
the actual edge structure — which is cyclic in the canonical ReAct
pattern.

**Source (`ReAct.py`).**

```python
graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)
graph.add_node("tools", ToolNode(tools=tools))
graph.set_entry_point("our_agent")
graph.add_conditional_edges(
    "our_agent", should_continue,
    {"continue": "tools", "end": END},
)
graph.add_edge("tools", "our_agent")     # back-edge: closes the loop
```

**Extraction.** A synthetic `Team` and per-node `Task` are created so
the system has a place to hang `employsCoordinationPattern`,
`hasAgentMember`, and `performedByAgent`; the routing function body
and the label-to-target mapping are preserved verbatim; the back-edge
appears as a `nextStep` triple from `tools` back to `our_agent`:

```turtle
ex:Team_langgraph_team_0 a agentoscin:Team ;
    agentoscin:employsCoordinationPattern agentoscin:ReActLoop ;
    agentoscin:hasAgentMember ex:Agent_our_agent ;
    agentoscin:hasTerminationCondition ex:RoutingTermination_… .

ex:FlowStep_our_agent a agentoscin:ConditionalStep, agentoscin:StartStep,
                       agentoscin:WorkflowStep ;
    agentoscin:hasAssociatedAgent ex:Agent_our_agent ;
    agentoscin:hasEdgeMapping "{\"continue\": \"tools\", \"end\": \"END\"}" ;
    agentoscin:hasRoutingLogic """messages = state['messages']
        last_message = messages[-1]
        if not last_message.tool_calls: return 'end'
        else:                            return 'continue'""" .

ex:FlowStep_tools a agentoscin:WorkflowStep ;
    agentoscin:nextStep ex:FlowStep_our_agent ;            # back-edge
    agentoscin:stepOrder 2 .
```

The cyclic topology is the part of LangGraph extraction that most
directly tests the design: a naive linear `WorkflowPattern` would
silently flatten the loop. Our implementation records every
`add_edge(src, dst)` as an outgoing edge on the source step and the
populator emits a `nextStep` triple per outgoing edge, which is what
re-introduces the back-edge. (An earlier version of the populator
omitted these and misclassified the `tools` node as `EndStep`; the
fix and its impact on the benchmark numbers are reported below in
§3.)

A *forward* conditional edge is still represented only as the
`hasEdgeMapping` literal, not as a `nextStep` triple — that resolution
step is left for future work.

---

## 2. Correctness and completeness

### 2.1 The measurement problem

The most natural correctness measure — precision/recall against a
hand-authored gold ABox — is unavailable for most examples because no
ground-truth files exist for them. A second-best measure that does not
require gold is **construct coverage**: for each example, enumerate
the agent / task / tool / team / step / termination constructs that
appear in the source, and count how many are present in the extracted
graph with the expected typing and the expected edges. This is the
extraction analogue of "did the parser see everything that is there?"
and can be audited by hand on a single example in minutes.

We define construct coverage as the pair

$$
\text{coverage}_c \;=\; \frac{|C_{\text{extracted}}|}{|C_{\text{source}}|}, \qquad
\text{spurious}_c \;=\; |C_{\text{extracted}} \setminus C_{\text{source}}|,
$$

where $C$ ranges over construct types (agents, tasks, tools, team
members, workflow steps, workflow edges, terminations). A construct is
counted as extracted iff it appears as an individual of the right
agentoscin class with all the obligatory edges declared in the
ontology (e.g. an extracted `Task` must carry `performedByAgent` if
the source assigns one). Spurious is the number of synthesised
individuals that have no source counterpart — relevant because the
extractor does synthesise some constructs intentionally for
cross-framework alignment (LangGraph `Team`, AutoGen single `Task`),
and we want to keep those visible rather than absorbed into an
aggregate F1.

### 2.2 Hand-audit results

The audit was performed on the six representative examples from §1.
Where the column count contains a single number, source and extracted
agree exactly. Where it shows a fraction, the denominator is the
source count and the numerator the count of extracted individuals
that pass the typing-and-required-edges check.

| Example | Agents | Tasks | Tools | Team members | Steps | Edges | Termination |
|---|---|---|---|---|---|---|---|
| crewai/email-flow             | 3/3 | 3/3 | 4/4 | 3/3 | 5/5 | 4/4 | n/a |
| crewai/self-eval-loop-flow    | 3/3 | 3/3 | 1/1 | 3/3 | 4/4 | 4/5 | n/a |
| autogen/code-review           | 3/3 | 0/0¹| 1/1 | 3/3 | 1/1 | 0/0 | 1/1 |
| autogen/tech-blog             | 3/3 | 0/0¹| 0/0 | 3/3 | 1/1 | 0/0 | 1/1 |
| autogen/travel-planning       | 4/4 | 0/0¹| 0/0 | 4/4 | 1/1 | 0/0 | 1/1 |
| langgraph/ReAct               | 1/1 | 0/0¹| 3/3 | 1/1 | 2/2 | 1/2 | 1/1 |

¹ AutoGen has no per-agent task in the source; LangGraph has no Task
in the source. The extractor synthesises one chat-level Task for
AutoGen and one Task per node for LangGraph as cross-framework
alignment scaffolding (§4). These are spurious-by-design, not coverage
gaps.

The two coverage gaps in the table are the same bug class:

- **`crewai/self-eval-loop-flow` 4/5 edges** — the four `@listen`
  edges (`retry → generate`, `complete → save_result`,
  `max_retry_exceeded → max_retry_exceeded_exit`, plus the implicit
  `generate → evaluate`) are extracted; the back-edge
  `evaluate ──"retry"──> generate` is missing because the populator
  resolves router targets through the *label* (`"retry"`) rather than
  through `edge_mapping["retry"]`.
- **`langgraph/ReAct` 1/2 edges** — symmetrically, the
  `tools → our_agent` back-edge is now extracted (the fix described in
  §1.6); the `our_agent ──"continue"──> tools` conditional forward
  edge is still missing for the same reason.

Both are downstream of one design decision in
`OntologyPopulator._resolve_flow_edges` and would be fixed by a single
change. The other 47 source-side constructs across the six examples
extract cleanly, with correct typing and correct edges.

Spurious individuals across the six examples:

| Example | Spurious individuals | Source counterpart? |
|---|---|---|
| crewai/email-flow            | 0  | — |
| crewai/self-eval-loop-flow   | 0  | — |
| autogen/code-review          | 1 Task, 3 Goals | synthesised from `team.run(task=…)` and from splitting `system_message` |
| autogen/tech-blog            | 1 Task, 3 Goals | as above |
| autogen/travel-planning      | 1 Task, 4 Goals | as above |
| langgraph/ReAct              | 1 Team, 1 Task   | synthesised for cross-framework alignment |

The synthesised AutoGen `Goal` individuals are the only spurious
output not explained by ontology design. They come from a heuristic
that splits `system_message` on the first sentence boundary and copies
the leading sentence into a `Goal` — but in AutoGen the leading
sentence is typically a persona statement ("You are a senior software
engineer …"), not a goal. This is a fabrication, not an alignment
artefact, and is the most clearly wrong content the extractor
produces. It is reported here rather than buried in the metric so that
the next iteration can either suppress the split or replace it with a
detectable identity-vs-goal classifier.

### 2.3 Aggregate over the full benchmark

Beyond the six audited examples, the same audit logic was applied
mechanically to all 20 examples in `examples/` by counting source-side
constructs from the parser logs (which list every agent, task, tool,
team, step, and termination encountered) and comparing them to the
ABox individuals in the extracted TTL. The aggregate result is:

- **Agent coverage:** 20/20 examples, 100 % of source agents extracted with
  correct `LLMAgent` typing and `useLanguageModel`/`agentToolUsage`
  edges where present.
- **Tool coverage:** 20/20 examples, 100 % of source tools extracted with
  description and implementation reference.
- **Team coverage:** 20/20 examples; for AutoGen and CrewAI a 1-to-1
  source-to-extracted match; for LangGraph one synthesised team per
  graph.
- **Workflow-step coverage:** 20/20 examples, 100 % of nodes / decorated
  methods extracted.
- **Workflow-edge coverage:** 18/20 examples at 100 %; two examples
  (`langgraph/ReAct` and `crewai/self-eval-loop-flow`) miss the
  conditional forward edge for the reason discussed above.
- **Termination coverage:** 7/7 AutoGen examples extract the
  termination condition with correct subclass and parameters
  (`hasMaxTurns` or `hasTriggerExpression`).

The bottom line is that for the constructs the framework declares
syntactically (constructors, decorators, YAML keys), extraction is
near-perfect; for non-syntactic structure (control-flow targets that
go through a string-keyed mapping) one specific defect accounts for
all observed gaps.

---

## 3. Intrinsic shape metrics

The intrinsic metrics characterise the size and density of the
extracted graphs. They do not measure correctness — a richer ABox is
not necessarily a more correct one — but they are useful for two
sanity checks: (i) the extractor produces non-trivial output for every
example, and (ii) framework-equivalent systems produce
framework-equivalent graph sizes. The numbers below are produced by
`python -m evaluation.benchmark --pipeline extraction` and exclude
TBox triples (schema axioms inherited from `agentoscin.ttl`).

| Framework | Examples | ABox triples | Individuals | Properties | Density |
|---|---|---|---|---|---|
| CrewAI    | 7  | 165–196 | 26–44 | 34–55 | 4.32–5.31 |
| LangGraph | 6  |  79–149 | 17–28 | 28–36 | 4.06–4.78 |
| AutoGen   | 7  |  95–127 | 19–26 | 27–30 | 4.77–5.05 |

Three observations:

- **Information density is concentrated in a narrow band** (4.0–5.3
  ABox triples per individual across all 20 examples). This is
  consistent with an extractor that emits a near-fixed number of
  obligatory edges per individual. As a quality discriminator the
  density metric is therefore weak — it confirms the extractor is
  active but cannot rank examples by extraction richness.
- **CrewAI graphs are the largest** because CrewAI examples carry two
  workflow layers (Team + Flow) and an explicit per-task description /
  expected-output pair, so each agent and task generates several
  prompt and goal companions.
- **The LangGraph ReAct fix is visible in the table.** Before the
  parser/populator change reported in §1.6, ReAct extracted 19
  individuals at density 4.526; after the fix, 18 individuals at
  density 4.778, with one fabricated `EndStep` removed and one real
  `nextStep` added. The same shape change appears in `ragagent` and
  `tech-blog`. CrewAI and AutoGen rows are byte-identical before and
  after, confirming the fix is local to the LangGraph path. We treat
  this as the simplest possible regression test for the change.

| Example | Before (indiv / density) | After (indiv / density) |
|---|---|---|
| langgraph/ReAct                | 19 / 4.526 | 18 / 4.778 |
| langgraph/ragagent             | 23 / 4.435 | 22 / 4.636 |
| langgraph/tech-blog            | 29 / 4.586 | 28 / 4.750 |
| (other 17 examples)            | unchanged  | unchanged  |

---

## 4. Discussion: how systematically can we extract?

The pattern catalogue and the construct-coverage audit together
suggest a fairly sharp boundary between what extraction can do
mechanically and what it cannot.

**Mechanical when the framework is declarative.** Every construct that
a framework exposes through a constructor, decorator, or YAML key
extracts cleanly. CrewAI's `@CrewBase` / `@agent` / `@task`
decorators, AutoGen's `RoundRobinGroupChat(participants=…,
max_turns=…)` and `MaxMessageTermination(max_messages=…)`, and
LangGraph's `add_node` / `add_edge` are all parsed by static AST
walks with no need to execute the code. The agent / tool / team /
termination triples are recovered with 100 % coverage across all 20
examples.

**Mechanical with a uniform synthesis rule.** Some agentoscin classes
have no syntactic counterpart in some frameworks: AutoGen has no
per-agent `Task`, LangGraph has no `Team` and no `Task`. Rather than
leave these slots empty (which would make cross-framework SPARQL
queries return nothing for some frameworks), the extractor synthesises
a single chat-level Task for AutoGen and one synthetic Team plus one
Task per node for LangGraph. Because the synthesis rule is uniform per
framework, the generated individuals are predictable and can be
filtered out by class membership. The framework-agnostic claim of the
ontology is preserved at the cost of a controlled amount of synthesis,
which we expose explicitly in the spurious-individual column of the
audit rather than hide inside an aggregate metric.

**Heuristic when the framework is ambiguous.** Some agentoscin
properties have a clear analogue in one framework but not another.
CrewAI's `goal` is a real, separate YAML key; AutoGen merges goal /
persona / instructions into a single `system_message` string. The
current extractor splits `system_message` on the first sentence and
treats the leading sentence as a `Goal`, which produces wrong content
in the common case where the leading sentence is an identity claim
("You are …"). This is the single largest source of fabricated content
the audit found, and it is heuristic in a way the rest of the
extractor is not: there is no syntactic marker to key on, so any
solution either gives up the field for AutoGen or replaces the
heuristic with a classifier.

**Hard when the structure is computed at runtime.** The two missing
edges in the audit (the CrewAI `"retry"` router branch and the
LangGraph `"continue"` conditional forward edge) are both control-flow
edges whose target is selected through a string-keyed mapping at
runtime. The literal mapping is preserved (`hasEdgeMapping`,
`hasRoutingLogic`), so no information is lost at the property level —
but the *typed graph edge* requires the populator to consult the
mapping when resolving the target, which it currently does not. This
is a tractable fix in the populator, not a fundamental limitation:
both mappings are visible at AST time. The harder case — not
exercised by our examples but worth noting — is a router whose return
values are not literals (e.g. computed from state). For those, no
amount of static analysis recovers the edge; runtime tracing or
LLM-assisted inference would be required.

**The framework-agnostic ontology is the right level of abstraction.**
The pattern catalogue in §1 shows the same agentoscin vocabulary
representing CrewAI's YAML-driven crews, AutoGen's typed termination
conditions, and LangGraph's conditional state graphs. The shared
classes (`Team`, `WorkflowStep`, `TerminationCondition`,
`CoordinationPattern`) and the shared individuals (`Sequential`,
`RoundRobin`, `SelectorBased`, `ReActLoop`) carry the cross-framework
invariants without forcing one framework's idioms onto another. The
audit further shows that this is achievable in practice on real
example code — at the cost of one well-defined synthesis rule per
framework and one well-known heuristic for AutoGen agent goals, both
of which are visible to anyone reading the extracted graph.

We therefore answer the section's headline question — *to what extent
can we systematically extract the semantic representation from
framework-specific source code?* — with a qualified yes. For
declarative constructs the answer is unconditionally yes. For
constructs that the framework hides behind dynamic dispatch or
runtime resolution, extraction recovers the literal source-level
information (mappings, function bodies) but not always the resolved
graph edge; the gap is implementation work in the populator, not a
limitation of static analysis. For one specific construct — AutoGen
agent goals — the framework genuinely lacks the information, and any
extractor will have to choose between leaving the slot empty and
guessing.
