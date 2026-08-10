"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()



class TechBlogState(BaseModel):
    """Flow state — customize fields as needed."""
    draft: str = ""
    final_post: str = ""
    messages: list = []
    research: str = ""
    topic: str = ""


class StateGraph(Flow[TechBlogState]):

    @start()
    def researcher(self):
        """
        Read the topic from self.state and produce a research summary into self.state.research.
        This is a deterministic, local implementation to simulate the original LLM behavior.
        """
        topic = getattr(self, "state", None)
        if topic is None:
            raise RuntimeError("State not initialized")
        topic = self.state.topic or "Agentic AI Frameworks"
        # Simulated research summary
        research_summary = (
            f"Topic: {topic}\n\n"
            "Summary:\n"
            "Agentic AI frameworks enable systems composed of multiple interacting agents that "
            "coordinate to achieve complex goals. Such frameworks define roles, delegation "
            "strategies, and orchestration patterns (e.g., sequential workflows). Core components "
            "include task decomposition, inter-agent communication, shared state management, and "
            "termination conditions. Practical applications range from automated research and "
            "content generation to multi-step decision making in software agents. Key considerations "
            "are robustness (handling failures), interpretability (explaining agent decisions), "
            "and cost-effective use of language models."
        )
        self.state.research = research_summary
        print("[researcher] Completed research generation.")

    @listen(researcher)
    def writer(self):
        """
        Use self.state.research to produce a draft into self.state.draft.
        This simulates the writer LLM creating a 500-word post (shortened here).
        """
        if getattr(self, "state", None) is None:
            raise RuntimeError("State not initialized")
        research = self.state.research
        topic = self.state.topic or "Agentic AI Frameworks"
        draft = (
            f"Draft Blog Post on {topic}\n\n"
            "Introduction:\n"
            f"{research.splitlines()[2] if research else ''}\n\n"
            "Body:\n"
            "Agentic AI frameworks represent a shift toward modular, role-driven AI systems. "
            "By decomposing problems into tasks handled by specialized agents, teams can scale "
            "complex workflows while maintaining clarity of responsibility. Communication protocols "
            "and shared state ensure agents remain synchronized and can build upon each other's work.\n\n"
            "Conclusion:\n"
            "When designed thoughtfully, agentic systems can accelerate research and engineering, "
            "but they require careful orchestration and monitoring."
        )
        self.state.draft = draft
        print("[writer] Completed draft generation.")

    @listen(writer)
    def editor(self):
        """
        Polish self.state.draft into self.state.final_post.
        This simulates the editor LLM producing a final polished post.
        """
        if getattr(self, "state", None) is None:
            raise RuntimeError("State not initialized")
        draft = self.state.draft
        # Simple polishing: ensure paragraphs are well spaced and fix obvious spacing
        polished = "\n\n".join([p.strip().capitalize() for p in draft.split("\n\n") if p.strip()])
        # Append a short byline
        polished += "\n\n---\nFinalized by the StateGraph editorial agent."
        self.state.final_post = polished
        print("[editor] Completed final post polishing.")

    # Override kickoff to run the steps deterministically and print the result.
    def kickoff(self):
        print("Starting CrewAI StateGraph Tech Blog Generation...")
        # Initialize state with a representative concrete input
        self.state = TechBlogState(topic="Agentic AI Frameworks")
        # Run the steps sequentially
        try:
            self.researcher()
            self.writer()
            self.editor()
        except Exception as e:
            print("Error during flow execution:", e)
            raise
        print("Completed!")
        # Print the resulting final_post
        print(self.state.final_post)


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
