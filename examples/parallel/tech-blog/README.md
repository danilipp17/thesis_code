# tech-blog

**Origin:** CrewAI. **Scenario:** linear 3-agent pipeline.

Three agents collaborate sequentially on a single topic ("Agentic AI
Frameworks"):

1. **researcher** — gather information on the topic, output a research summary.
2. **writer** — turn the summary into a ~500-word draft blog post.
3. **editor** — polish the draft into a publishable final version.

## Framework variants

| variant   | source                                         | flavour                                         |
|-----------|------------------------------------------------|-------------------------------------------------|
| crewai    | `examples/parallel/tech-blog/crewai/source_files`       | `TechBlogFlow(Flow[TechBlogState])` wrapping a `@CrewBase TechBlogCrew` with YAML-configured agents and tasks; `Process.sequential`; tasks chained via `context=` |
| langgraph | `examples/langgraph/tech-blog/source_files`    | `StateGraph` with TypedDict state, explicit nodes and edges |
| autogen   | `examples/autogen/tech-blog/source_files`      | `RoundRobinGroupChat` with `MaxMessageTermination(max_messages=4)`, agents carry `system_message` prompts |

All three were authored (CrewAI variant originally, the other two as ports)
to produce a recognisably tech-blog-shaped output for the same input topic.
Equivalence is by inspection only.
