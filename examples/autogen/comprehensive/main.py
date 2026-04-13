from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager


def calculate_tax(amount: float) -> float:
    """Calculates standard tax rate."""
    return amount * 0.19


def db_lookup(query: str) -> str:
    """Looks up database records."""
    return "Dummy data"


# AssistantAgent translates to LLMAgent
researcher = AssistantAgent(
    name="Researcher",
    system_message="You are a data researcher. Find relevant information.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": "dummy"}]},
)
researcher.register_function(function_map={"db_lookup": db_lookup})

analyst = AssistantAgent(
    name="Analyst",
    system_message="You analyze data. Tax calculations are your specialty.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": "dummy"}]},
)
analyst.register_function(function_map={"calculate_tax": calculate_tax})

# UserProxyAgent translates to an Agent with human interaction / Checkpoint
user_proxy = UserProxyAgent(
    name="Admin",
    system_message="A human admin overseeing the group.",
    code_execution_config=False,
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
)

# GroupChat translates to Team
groupchat = GroupChat(
    agents=[user_proxy, researcher, analyst], messages=[], max_round=15
)

# GroupChatManager translates to Orchestrator/Manager
manager = GroupChatManager(
    groupchat=groupchat,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": "dummy"}]},
)

if __name__ == "__main__":
    user_proxy.initiate_chat(
        manager, message="Please look up the revenue and calculate the tax."
    )
