"""
Auto-generated CrewAI entry point.
"""

from crews.tech_blog_crew.tech_blog_crew import TechBlogCrew


def kickoff():
    crew = TechBlogCrew()
    print("Starting tech blog generation...")
    result = crew.crew().kickoff(inputs={"topic": "Agentic AI Frameworks"})
    print("Completed!")
    print(result.raw)


if __name__ == "__main__":
    kickoff()
