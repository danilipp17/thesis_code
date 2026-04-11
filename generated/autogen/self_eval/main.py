"""
Auto-generated AutoGen application: SelfEvaluationLoopSystem
"""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from tools import character_counter_tool

llm_config = {"model": "gpt-4o"}  # TODO: configure model

shakespearean_bard = AssistantAgent(
    name="Shakespearean Bard",
    system_message="""Thou art a witty bard, renowned for turning the mundane into the magnificent with thy playful jests and biting sarcasm. Armed with wit and wisdom, thou dost revel in the creation of humorous quips most pleasing to the ear.""",
    llm_config=llm_config,
)

x_post_verifier = AssistantAgent(
    name="X Post Verifier",
    system_message="""You are a careful reviewer, skilled at understanding the core message of a post.  Your job is to maintain the clarity and brevity of the post by ensuring it contains no emojis,  unnecessary commentary, or excessive verbosity.""",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

groupchat_shakespearean_xpost_crew = GroupChat(
    agents=[user_proxy, shakespearean_bard],
    messages=[],
    max_round=10,
)

manager_shakespearean_xpost_crew = GroupChatManager(
    groupchat=groupchat_shakespearean_xpost_crew,
    llm_config=llm_config,
)

groupchat_xpost_review_crew = GroupChat(
    agents=[user_proxy, x_post_verifier],
    messages=[],
    max_round=10,
)

manager_xpost_review_crew = GroupChatManager(
    groupchat=groupchat_xpost_review_crew,
    llm_config=llm_config,
)

# Register tools
shakespearean_bard.register_for_llm(
    name="character_counter_tool",
    description="Counts the number of characters in a given string.",
)(character_counter_tool)
user_proxy.register_for_execution()(character_counter_tool)


if __name__ == "__main__":
    user_proxy.initiate_chat(
        manager_shakespearean_xpost_crew,
        message="Start the task.",  # TODO: provide initial message
    )
