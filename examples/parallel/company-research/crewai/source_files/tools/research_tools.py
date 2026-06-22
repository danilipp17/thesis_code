"""Research tools exposed as CrewAI tools (port of the AutoGen FunctionTools)."""

from crewai.tools import tool


@tool("google_search")
def google_search(query: str, num_results: int = 2, max_chars: int = 500) -> list:
    """Search Google for information, returns results with a snippet and body content"""
    import os
    import time

    import requests
    from bs4 import BeautifulSoup

    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not search_engine_id:
        raise ValueError("API key or Search Engine ID not found in environment variables")

    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {"key": str(api_key), "cx": str(search_engine_id), "q": str(query), "num": str(num_results)}

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error in API request: {response.status_code}")

    results = response.json().get("items", [])

    def get_page_content(link: str) -> str:
        try:
            r = requests.get(link, timeout=10)
            soup = BeautifulSoup(r.content, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            words = text.split()
            content = ""
            for word in words:
                if len(content) + len(word) + 1 > max_chars:
                    break
                content += " " + word
            return content.strip()
        except Exception:
            return ""

    enriched = []
    for item in results:
        body = get_page_content(item["link"])
        enriched.append(
            {"title": item["title"], "link": item["link"], "snippet": item["snippet"], "body": body}
        )
        time.sleep(1)
    return enriched


@tool("analyze_stock")
def analyze_stock(ticker: str) -> dict:
    """Analyze stock data and generate a plot"""
    import os
    from datetime import datetime, timedelta

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import yfinance as yf
    from pytz import timezone

    stock = yf.Ticker(ticker)
    end_date = datetime.now(timezone("UTC"))
    start_date = end_date - timedelta(days=365)
    hist = stock.history(start=start_date, end=end_date)
    if hist.empty:
        return {"error": "No historical data available for the specified ticker."}

    current_price = stock.info.get("currentPrice", hist["Close"].iloc[-1])
    ma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
    ma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]
    trend = "Upward" if ma_50 > ma_200 else "Downward" if ma_50 < ma_200 else "Neutral"
    daily_returns = hist["Close"].pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252)

    result = {
        "ticker": ticker,
        "current_price": current_price,
        "50_day_ma": ma_50,
        "200_day_ma": ma_200,
        "trend": trend,
        "volatility": volatility,
    }
    for key, value in result.items():
        if isinstance(value, np.generic):
            result[key] = value.item()

    plt.figure(figsize=(12, 6))
    plt.plot(hist.index, hist["Close"], label="Close Price")
    plt.title(f"{ticker} Stock Price (Past Year)")
    plt.legend()
    os.makedirs("coding", exist_ok=True)
    plot_file_path = f"coding/{ticker}_stockprice.png"
    plt.savefig(plot_file_path)
    result["plot_file_path"] = plot_file_path
    return result
