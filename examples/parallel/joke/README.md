# joke

**Origin:** LangGraph. **Scenario:** small single-topic joke generator with
a conditional refinement loop.

* generate an initial short joke about a topic ("cats");
* if the joke has a punchline (contains `?` or `!`) — done;
* otherwise improve it (add wordplay), then polish it (add a twist).

## Framework variants

| variant   | source                                         | flavour                                                                                  |
|-----------|------------------------------------------------|------------------------------------------------------------------------------------------|
| langgraph | `examples/langgraph/joke/joke.py`              | `StateGraph` with `TypedDict` state and `add_conditional_edges(check_punchline, …)` gate |
| crewai    | `examples/parallel/joke/crewai/source_files`   | `JokeFlow(Flow[JokeState])` with `@start`/`@router`/`@listen`; gate preserved via `@router(generate_joke)` returning `"Pass"`/`"Fail"`; each step delegates to its own YAML-configured `@CrewBase` crew under `crews/{generate,improve,polish}_joke_crew/` |
| autogen   | `examples/parallel/joke/autogen/source_files`  | `RoundRobinGroupChat` over 3 `AssistantAgent`s + `MaxMessageTermination(4)`; the conditional gate is **not directly representable** in RoundRobin and is dropped — itself a finding |

Equivalence is by inspection only.
