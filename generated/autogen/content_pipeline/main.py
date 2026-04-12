"""
Auto-generated AutoGen application: ContentPipelineSystem
"""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from tools import web_search_tool, word_count_tool

llm_config = {"model": "gpt-4o"}

content_writer = AssistantAgent(
    name="Content Writer",
    system_message="""Role: Content Writer
Goal: Transform research findings into engaging, well-structured articles that are informative and accessible to a broad audience.
You are a seasoned content writer with a talent for making complex topics accessible. You follow best practices for online content including clear headings, concise paragraphs, and actionable insights.""",
    llm_config=llm_config,
)

quality_reviewer = AssistantAgent(
    name="Quality Assurance Editor",
    system_message="""Role: Quality Assurance Editor
Goal: Review content for factual accuracy, grammar, style consistency, and adherence to the content brief. Provide a quality score and actionable feedback.
You are a meticulous editor with years of experience in publishing. You have a keen eye for detail, ensuring every piece meets high editorial standards before publication.""",
    llm_config=llm_config,
)

research_analyst = AssistantAgent(
    name="Senior Research Analyst",
    system_message="""Role: Senior Research Analyst
Goal: Research and gather comprehensive, accurate information on a given topic using web search tools. Provide structured findings with sources.
You are an experienced research analyst with a background in investigative journalism. You excel at finding reliable sources, cross-referencing information, and presenting facts in a clear, structured manner.""",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

groupchat_content_pipeline_crew = GroupChat(
    agents=[user_proxy, content_writer, quality_reviewer, research_analyst],
    messages=[],
    max_round=10,
)

manager_content_pipeline_crew = GroupChatManager(
    groupchat=groupchat_content_pipeline_crew,
    llm_config=llm_config,
)

# Register tools
research_analyst.register_for_llm(
    name="web_search_tool",
    description="Search the web for information on a given query. Returns titles, snippets, and URLs of relevant results.",
)(web_search_tool)
user_proxy.register_for_execution()(web_search_tool)

content_writer.register_for_llm(
    name="word_count_tool",
    description="Counts the number of words in a given text.",
)(word_count_tool)
quality_reviewer.register_for_llm(
    name="word_count_tool",
    description="Counts the number of words in a given text.",
)(word_count_tool)
user_proxy.register_for_execution()(word_count_tool)


if __name__ == "__main__":
    user_proxy.initiate_chat(
        manager_content_pipeline_crew,
        message="Start the task.",  # TODO: provide initial message
    )
