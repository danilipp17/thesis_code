"""
Auto-generated CrewAI entry point.
"""

import dotenv

dotenv.load_dotenv()

from crews.tech_blog_crew.tech_blog_crew import TechBlogCrew


def kickoff():
    result = TechBlogCrew().crew().kickoff()
    print(result)


if __name__ == "__main__":
    kickoff()
