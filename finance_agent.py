import os
import re
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import AgentType, initialize_agent
from langchain_community.chat_models import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun, tool


@tool
def search_ticker(company_name: str) -> str:
    search = DuckDuckGoSearchRun()
    # Enhance the search query for better relevance
    search_results_string = search.run(company_name + " stock ticker symbol")

    # Common regex patterns for stock tickers
    ticker_patterns = [
        # Ticker inside parentheses (e.g., Company Name (AMZN))
        r'\(([A-Z]{1,5})\)',
        # Ticker following keywords like "ticker:", "symbol:", "stock:"
        r'(?:ticker|symbol|stock)\s*[:\-]?\s*([A-Z]{1,5})\b',
        # Ticker as a standalone word, potentially followed by "stock", "ticker", "symbol"
        r'\b([A-Z]{2,5})\b(?:\s+(?:stock|ticker|symbol))?'
    ]

    for pattern in ticker_patterns:
        match = re.search(pattern, search_results_string, re.IGNORECASE)
        if match:
            # Return the first captured group, which is the ticker, ensured uppercase
            return match.group(1).upper()

    # Attempt to specifically handle the "MarketWatch" case,
    # re-interpreting the original logic for unstructured string data.
    # This tries to find a ticker in parentheses near "MarketWatch".
    if "marketwatch" in search_results_string.lower():
        mw_ticker_pattern = r"MarketWatch.*?\((\b[A-Z]{1,5}\b)\)"
        match = re.search(mw_ticker_pattern, search_results_string, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    # Final fallback: Look for any sequence of 2-5 uppercase letters.
    # Filter out common noise like currencies or general financial terms.
    fallback_ticker_pattern = r'\b[A-Z]{2,5}\b'
    potential_tickers = re.findall(fallback_ticker_pattern, search_results_string)
    
    # Filter out common financial noise words that are not tickers
    noise_words = {
        "NYSE", "NASDAQ", "LSE", "TSX", "ASX", "INDEX", "MARKET", "STOCK", "TICKER",
        "PRICE", "NEWS", "OPEN", "HIGH", "LOW", "VOLUME", "TODAY", "LAST", "CLOSE",
        "USD", "GBP", "EUR", "CAD", "AUD", "JPY", "CNY", "BRL", "INR", "MXN", "ZAR",
        "FOREX", "FUND", "ETFS", "DATA", "RATE", "GAIN", "LOSS", "Q1", "Q2", "Q3", "Q4"
    }
    
    for ticker in potential_tickers:
        if ticker.upper() not in noise_words:
            return ticker.upper()

    return "No ticker found"


def run_finance_agent():
    llm = ChatOpenAI(temperature=0.0)
    # Correctly provide the custom tool directly to the agent.
    # The original `load_tools(["search_ticker"], llm=llm)` would not correctly
    # load a locally defined @tool function. This ensures the agent
    # actually uses the custom 'search_ticker' tool.
    tools = [search_ticker]

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    output = agent.run("what is the ticker of Amazon")
    print(output)


if __name__ == "__main__":
    run_finance_agent()