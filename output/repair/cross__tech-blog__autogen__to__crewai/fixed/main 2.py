"""
Auto-generated CrewAI Flow: AutoGenFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()


class AutoGenFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class AutoGenFlow(Flow[AutoGenFlowState]):

    @start()
    def run_team(self):
        """
        Simulated run of the RoundRobinGroupChat crew for a representative task.
        This step is implemented deterministically so the module can run end-to-end
        without external LLM calls. It prints the sequence of messages that would
        be produced by the Researcher, Writer, and Editor agents.
        """
        task = (
            "We need a blog post about Agentic AI Frameworks. "
            "Please research, write, and edit."
        )

        # Deterministic, representative outputs for each role.
        researcher_output = (
            "Research Summary:\n\n"
            "Agentic AI frameworks are systems that enable AI components to act "
            "autonomously toward high-level objectives by decomposing tasks, "
            "delegating sub-tasks, maintaining state, and interacting with external "
            "tools and environments. Core components include a task planner/orchestrator, "
            "a set of specialist agents or modules (for research, writing, editing, tool use), "
            "memory for storing context and intermediate results, and connectors to external "
            "APIs and data sources.\n\n"
            "Benefits: they accelerate complex workflows, allow parallelization of subtasks, "
            "and can produce higher-quality outputs by leveraging role specialization. "
            "Risks include unintended actions if objectives are underspecified, cascading "
            "errors across agents, and challenges in interpretability and safety assurance.\n\n"
            "Use cases: automated content generation pipelines, scientific literature reviews, "
            "multi-step software engineering assistants, and complex operational automation. "
            "Best practices: explicit task specifications, step limits or termination conditions, "
            "robust validation/check steps, and human-in-the-loop oversight for high-stakes tasks."
        )

        writer_output = (
            "Blog Post Draft:\n\n"
            "Agentic AI frameworks represent a new paradigm in applied artificial intelligence, "
            "designed to tackle complex, multi-step objectives by coordinating specialized AI "
            "components. Rather than relying on a single monolithic model to manage every facet "
            "of a task, these frameworks break problems down into sub-tasks, assign those tasks "
            "to purpose-built agents, and orchestrate their efforts to produce coherent results.\n\n"
            "At the heart of an agentic system is an orchestrator or planner that reasons about "
            "goals, sequences work, and monitors progress. Agents might include researchers that "
            "gather and synthesize information, writers that draft content, and editors that refine "
            "and validate outputs. Memory systems and tool integrations (e.g., web search, code "
            "execution, or database access) enrich agents' capabilities and help maintain context "
            "across steps.\n\n"
            "When applied to content generation, an agentic approach can improve both the efficiency "
            "and quality of output: researchers can pull together authoritative sources, writers can "
            "focus on narrative and tone, and editors can enforce clarity and correctness. However, "
            "these benefits come with responsibilities—clear task definitions, safeguards to prevent "
            "undesired actions, and validation checkpoints are essential.\n\n"
            "In short, agentic AI frameworks offer a powerful way to structure AI-driven workflows, "
            "combining specialization, orchestration, and tool access to solve complex tasks more "
            "reliably than single-step approaches.\n\n"
            "WRITTEN"
        )

        editor_output = (
            "Final Polished Post:\n\n"
            "Agentic AI frameworks mark a transformative step in how we apply artificial intelligence "
            "to multifaceted problems. Instead of funneling every requirement through a single model, "
            "these frameworks divide work among specialized agents—such as researchers, writers, and "
            "editors—and coordinate them with an orchestrator that manages goals, sequencing, and "
            "validation.\n\n"
            "This modular approach delivers several advantages. Researchers can focus on sourcing and "
            "synthesizing reliable information, writers can craft engaging and structured narratives, and "
            "editors can ensure clarity, correctness, and tone. Together, these roles produce higher-quality "
            "content more efficiently. Memory systems and tool integrations further enhance performance by "
            "maintaining context and enabling capabilities like web search or code execution.\n\n"
            "Adoption of agentic systems also requires careful governance. Clear task specifications, "
            "termination conditions, and human oversight are crucial to mitigate risks such as unintended "
            "actions or cascading errors between agents. With these safeguards, agentic frameworks can be "
            "applied across domains—from automated content creation to research assistance and complex "
            "operational workflows—offering scalable, reliable, and interpretable AI collaboration.\n\n"
            "TERMINATE"
        )

        # Sequence of messages as the team would produce in a round-robin run.
        messages = [
            {"source": "Researcher", "content": researcher_output},
            {"source": "Writer", "content": writer_output},
            {"source": "Editor", "content": editor_output},
        ]

        # Print results to emulate the original program's behavior.
        print("Starting AutoGen Tech Blog Generation...")
        print(f"Task: {task}\n")
        for msg in messages:
            print(f"[{msg['source']}]: {msg['content']}\n")

        # Optionally return messages in case the Flow infrastructure expects a result.
        return {"messages": messages}


def kickoff():
    flow = AutoGenFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
