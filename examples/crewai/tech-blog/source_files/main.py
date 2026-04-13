import os
from dotenv import load_dotenv

load_dotenv()

from crews.tech_blog_crew import TechBlogCrew


def run():
    crew = TechBlogCrew()
    print("Starting tech blog generation...")
    result = crew.crew().kickoff(inputs={"topic": "Agentic AI Frameworks"})
    print("Completed!")
    print(result.raw)


if __name__ == "__main__":
    run()
