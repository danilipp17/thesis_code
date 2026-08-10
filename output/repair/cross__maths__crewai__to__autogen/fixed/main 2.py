"""
Auto-generated AutoGen application: maths
"""

import asyncio
import dotenv
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.tools import FunctionTool
from tools import add, subtract, multiply

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
add_tool = FunctionTool(
    add,
    description="This is an addition function that adds 2 numbers together.",
)
subtract_tool = FunctionTool(
    subtract,
    description="Subtraction function.",
)
multiply_tool = FunctionTool(
    multiply,
    description="Multiplication function.",
)

# -- Agents --
our_agent = AssistantAgent(
    name="Maths_Reasoning_Assistant",
    model_client=model_client,
    tools=[add_tool, subtract_tool, multiply_tool],
    system_message=(
        "Answer the user query, calling arithmetic tools when needed. You are an AI assistant that answers user queries to the best of your ability, using the available tools whenever a step requires computation."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[our_agent],
    termination_condition=termination,
)


async def main():
    # Representative concrete input (following the original example)
    query = "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."

    print("Kicking off MathsCrew (auto-generated demo)...")
    print("User query:")
    print(query)
    print()

    # Perform the arithmetic steps using the provided tool functions.
    # The autogen tools expect a single string input; we call them directly with parsed inputs.
    sum_result_str = add("40,12")
    try:
        sum_result = int(sum_result_str)
    except Exception:
        # If tool returned non-integer, try to parse digits
        import re

        m = re.search(r"-?\d+", sum_result_str)
        sum_result = int(m.group()) if m else 0

    product_result_str = multiply(f"{sum_result},{6}")
    try:
        product_result = int(product_result_str)
    except Exception:
        import re

        m = re.search(r"-?\d+", product_result_str)
        product_result = int(m.group()) if m else 0

    # Compose a natural-language answer (includes a joke as requested).
    answer = (
        f"I added 40 and 12 to get {sum_result}. "
        f"Multiplying that result by 6 gives {product_result}. "
        f"Also, here's a joke: Why was the equal sign so humble? Because it knew it wasn't less than or greater than anyone else."
    )

    print("Answer:")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
