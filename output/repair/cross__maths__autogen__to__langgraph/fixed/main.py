"""
Auto-generated LangGraph application: maths
"""

import dotenv
from typing import Annotated, TypedDict
import json
import ast

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools import add, subtract, multiply
from langgraph.prebuilt import ToolNode

class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [add, subtract, multiply]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def _call_llm(messages):
    """
    Helper to call the chat model and extract text in a few common return shapes.
    """
    # Try calling as a callable
    try:
        res = model(messages)
    except Exception:
        # Fallback to generate if available
        try:
            res = model.generate(messages)
        except Exception as e:
            raise

    # Try several common shapes
    # If LLM returned a plain string
    if isinstance(res, str):
        return res

    # If it's a message-like object with content
    if hasattr(res, "content"):
        return res.content

    # LangChain ChatResult style: .generations -> list[list[Generation]]
    if hasattr(res, "generations"):
        gens = res.generations
        if gens and len(gens) > 0 and len(gens[0]) > 0:
            g = gens[0][0]
            # Generation may have .text
            if hasattr(g, "text"):
                return g.text
            # Or a message object
            if hasattr(g, "message") and hasattr(g.message, "content"):
                return g.message.content

    # As a last resort, stringify
    return str(res)


def _safe_parse_plan(text: str):
    """
    Attempt to parse a model-produced plan. The model may produce valid JSON,
    or Python-literal dicts/quotes. Try robust strategies.
    """
    try:
        return json.loads(text)
    except Exception:
        # Try to fix common single-quote dicts
        try:
            return ast.literal_eval(text)
        except Exception:
            # Try minor sanitization: replace single quotes with double quotes
            try:
                return json.loads(text.replace("'", "\""))
            except Exception:
                raise ValueError("Could not parse plan from model output.") from None


def run_team(state: State) -> dict:
    """Subgraph node: run_team"""
    # Extract the user's task from the incoming messages; fallback to a default
    msgs = state.get("messages", [])
    task_text = None
    if isinstance(msgs, list) and msgs:
        # Find last HumanMessage-like object
        last = msgs[-1]
        task_text = getattr(last, "content", None) or str(last)
    if not task_text:
        task_text = "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."

    # First LLM call: ask for a strict JSON plan that uses tool steps (do not compute arithmetic yourself)
    system = SystemMessage(content=(
        "You are an assistant that must produce a machine-readable plan for solving the user's task. "
        "Respond with STRICT JSON (no explanatory text). The JSON object must have a top-level 'steps' array. "
        "Each step must be either a tool call: "
        "{\"action\": \"tool\", \"name\": <tool_name>, \"args\": [arg1, arg2, ...]} "
        "or a final step: {\"action\": \"final\", \"content_template\": <string>}. "
        "When you need to calculate numbers, use tool steps and do not compute numbers yourself."
    ))
    user = HumanMessage(content=(
        f"Task: {task_text}\n\n"
        "Produce a plan that uses the tools 'add', 'subtract', and 'multiply' for numeric operations. "
        "Example (illustrative): {\"steps\": [{\"action\":\"tool\",\"name\":\"add\",\"args\":[40,12]}, "
        "{\"action\":\"tool\",\"name\":\"multiply\",\"args\":[52,6]}, "
        "{\"action\":\"final\",\"content_template\":\"The final result is {result}. Also, tell a short joke: {joke}\"}]}\n\n"
        "Return STRICT JSON only."
    ))

    plan_text = _call_llm([system, user]).strip()

    # Parse the plan
    plan = _safe_parse_plan(plan_text)
    steps = plan.get("steps") if isinstance(plan, dict) else None
    if not steps or not isinstance(steps, list):
        raise ValueError("Plan did not contain a 'steps' list.")

    last_result = None
    tool_outputs = []
    for step in steps:
        if not isinstance(step, dict) or "action" not in step:
            continue
        if step["action"] == "tool":
            name = step.get("name")
            args = step.get("args", [])
            # Map tool name to actual function
            if name == "add":
                out = add(*args)
            elif name == "subtract":
                out = subtract(*args)
            elif name == "multiply":
                out = multiply(*args)
            else:
                raise ValueError(f"Unknown tool name: {name}")
            # Tools (per tools.py) return strings; try to interpret as int if numeric
            try:
                last_result = int(out)
            except Exception:
                try:
                    last_result = float(out)
                except Exception:
                    last_result = out
            tool_outputs.append({"name": name, "args": args, "output": out})
        elif step["action"] == "final":
            # Prepare final content template and ask model to render it using the computed result
            template = step.get("content_template", "")
            # Ask the model to produce the final message, injecting the result and asking for a joke
            final_system = SystemMessage(content="You are a helpful assistant. Use the provided context to produce the final answer.")
            context_lines = [
                f"Original task: {task_text}",
                f"Computed result (from tools): {last_result}",
                f"Tool outputs: {json.dumps(tool_outputs)}",
                "",
                "Render the final message by filling the template. The template may include {result} and {joke} tokens. "
                "Replace {result} with the numeric result and {joke} with a short, original joke. "
                "Provide a friendly final answer including the computation and the joke."
            ]
            final_prompt = HumanMessage(content="\n".join(context_lines) + "\n\nTemplate:\n" + template)
            final_text = _call_llm([final_system, final_prompt]).strip()

            # Return as an AIMessage so the top-level printer can extract .content
            try:
                from langchain_core.messages import AIMessage
                return {"messages": [AIMessage(content=final_text)]}
            except Exception:
                # Fallback in case AIMessage unavailable
                return {"messages": [{"content": final_text}]}

    # If no final step was provided, ask the model to summarise the result
    final_system = SystemMessage(content="You are a helpful assistant. Summarize the computed result and tell a short joke.")
    final_prompt = HumanMessage(content=(
        f"Original task: {task_text}\nComputed result: {last_result}\nPlease produce a friendly final message including the result and a short original joke."
    ))
    final_text = _call_llm([final_system, final_prompt]).strip()
    try:
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=final_text)]}
    except Exception:
        return {"messages": [{"content": final_text}]}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_team", run_team)
graph.add_node("tools", tool_node)

graph.add_edge(START, "run_team")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content=(
        "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
    ))]})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
