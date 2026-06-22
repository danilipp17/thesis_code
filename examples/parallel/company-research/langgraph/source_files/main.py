"""
company-research — LangGraph port of the AutoGen original.

Original: examples/parallel/company-research/autogen — a
RoundRobinGroupChat of three AssistantAgents (web search, stock
analysis, report) producing a financial report.

LangGraph mapping:
  - AutoGen RoundRobinGroupChat -> a StateGraph that runs three agent
    nodes in sequence (search_agent -> analysis_agent -> report_agent).
  - AutoGen AssistantAgents     -> node functions, each invoking a
    ChatOpenAI model; search/analysis bind their respective tool.
  - AutoGen FunctionTools       -> @tool callables (google_search,
    analyze_stock) bound to the relevant agent's model.
"""

import operator
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

load_dotenv()


@tool
def google_search(query: str, num_results: int = 2, max_chars: int = 500) -> list:
    """Search Google for information, returns results with a snippet and body content"""
    import os

    import requests
    from bs4 import BeautifulSoup

    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not search_engine_id:
        raise ValueError("API key or Search Engine ID not found in environment variables")
    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {"key": str(api_key), "cx": str(search_engine_id), "q": str(query), "num": str(num_results)}
    response = requests.get(url, params=params)
    results = response.json().get("items", [])
    enriched = []
    for item in results:
        try:
            r = requests.get(item["link"], timeout=10)
            soup = BeautifulSoup(r.content, "html.parser")
            body = " ".join(soup.get_text(separator=" ", strip=True).split())[:max_chars]
        except Exception:
            body = ""
        enriched.append({"title": item["title"], "link": item["link"], "snippet": item["snippet"], "body": body})
    return enriched


@tool
def analyze_stock(ticker: str) -> dict:
    """Analyze stock data and generate a plot"""
    from datetime import datetime, timedelta

    import numpy as np
    import yfinance as yf
    from pytz import timezone

    stock = yf.Ticker(ticker)
    end_date = datetime.now(timezone("UTC"))
    hist = stock.history(start=end_date - timedelta(days=365), end=end_date)
    if hist.empty:
        return {"error": "No historical data available for the specified ticker."}
    ma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
    ma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]
    trend = "Upward" if ma_50 > ma_200 else "Downward" if ma_50 < ma_200 else "Neutral"
    volatility = hist["Close"].pct_change().dropna().std() * np.sqrt(252)
    return {"ticker": ticker, "50_day_ma": float(ma_50), "200_day_ma": float(ma_200),
            "trend": trend, "volatility": float(volatility)}


tools = [google_search, analyze_stock]


class CompanyResearchState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    company: str
    search_results: str
    analysis: str
    report: str


def _run_with_tool(llm_with_tools, tool_fn, prompt):
    """Single-shot tool resolution: invoke, run any tool call, summarise."""
    response = llm_with_tools.invoke([HumanMessage(content=prompt)])
    if getattr(response, "tool_calls", None):
        results = [str(tool_fn.invoke(tc["args"])) for tc in response.tool_calls]
        response = llm_with_tools.invoke(
            [HumanMessage(content=prompt + "\n\nTool results:\n" + "\n".join(results))]
        )
    return response.content


def search_agent(state: CompanyResearchState):
    llm = ChatOpenAI(model="gpt-4o").bind_tools([google_search])
    company = state["company"]
    prompt = f"Search the web for the latest information about {company} and summarise the key findings."
    return {"search_results": _run_with_tool(llm, google_search, prompt)}


def analysis_agent(state: CompanyResearchState):
    llm = ChatOpenAI(model="gpt-4o").bind_tools([analyze_stock])
    company = state["company"]
    prompt = f"Analyze the stock for {company}: compute moving averages, volatility, and the overall trend."
    return {"analysis": _run_with_tool(llm, analyze_stock, prompt)}


def report_agent(state: CompanyResearchState):
    llm = ChatOpenAI(model="gpt-4o")
    prompt = (
        f"Write a comprehensive financial report on {state['company']} using the "
        f"web search findings and the stock analysis below.\n\n"
        f"SEARCH FINDINGS:\n{state['search_results']}\n\n"
        f"STOCK ANALYSIS:\n{state['analysis']}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"report": response.content}


graph = StateGraph(CompanyResearchState)
graph.add_node("search_agent", search_agent)
graph.add_node("analysis_agent", analysis_agent)
graph.add_node("report_agent", report_agent)

graph.set_entry_point("search_agent")
graph.add_edge("search_agent", "analysis_agent")
graph.add_edge("analysis_agent", "report_agent")
graph.add_edge("report_agent", END)

app = graph.compile()


def run():
    print("Starting LangGraph Company Research...")
    initial_state = {
        "messages": [],
        "company": "American Airlines",
        "search_results": "",
        "analysis": "",
        "report": "",
    }
    result = app.invoke(initial_state)
    print("Completed!")
    print(result["report"])


if __name__ == "__main__":
    run()
