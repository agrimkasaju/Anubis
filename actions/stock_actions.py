import yfinance as yf
from typing import Any


def get_stock_analysis(symbol: str) -> str:
    """
    Fetches real-time price, quarterly/annual financial health,
    analyst recommendations, and top news for a given stock ticker symbol.
    """
    try:
        ticker_symbol = (symbol or "").upper().strip()
        if not ticker_symbol:
            return "Error: No ticker symbol provided."

        ticker = yf.Ticker(ticker_symbol)
        info: Any = getattr(ticker, "info", {}) or {}

        # Fallbacks for modern yfinance which sometimes uses fast_info or raw attrs
        if not info:
            try:
                info = ticker.fast_info or {}
            except Exception:
                info = {}

        if not info or ("regularMarketPrice" not in info and "currentPrice" not in info and "last_price" not in info):
            return f"Error: Could not retrieve valid financial data for ticker '{symbol}'."

        # 1. Price & Valuations
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("last_price", "N/A")
        currency = info.get("currency", "USD")
        market_cap = info.get("marketCap", info.get("market_cap", 0))
        pe_ratio = info.get("trailingPE", info.get("pe_ratio", "N/A"))
        fifty_two_week_high = info.get("fiftyTwoWeekHigh", info.get("fifty_two_week_high", "N/A"))
        fifty_two_week_low = info.get("fiftyTwoWeekLow", info.get("fifty_two_week_low", "N/A"))

        # 2. Financial Metrics
        total_revenue = info.get("totalRevenue", info.get("total_revenue", 0))
        net_income = info.get("netIncomeToCommon", info.get("net_income", 0))
        profit_margins = info.get("profitMargins", info.get("profit_margins", None))

        def fmt_num(num):
            try:
                if isinstance(num, (int, float)) and num != 0:
                    if abs(num) >= 1e12:
                        return f"${num/1e12:.2f}T"
                    if abs(num) >= 1e9:
                        return f"${num/1e9:.2f}B"
                    if abs(num) >= 1e6:
                        return f"${num/1e6:.2f}M"
                return str(num)
            except Exception:
                return str(num)

        # 3. Analyst Viewpoints
        recommendation = str(info.get("recommendationKey", info.get("recommendation", "N/A"))).replace("_", " ").title()
        target_mean_price = info.get("targetMeanPrice", info.get("target_mean_price", "N/A"))
        num_analysts = info.get("numberOfAnalystOpinions", info.get("analyst_count", "N/A"))

        # 4. News Headlines
        news_summary = []
        try:
            raw_news = getattr(ticker, "news", []) or []
            for item in raw_news[:3]:
                title = item.get("title") or item.get("content", {}).get("title", "")
                publisher = item.get("publisher") or item.get("source") or item.get("content", {}).get("provider", {}).get("displayName", "")
                if title:
                    news_summary.append(f"- {title} (Source: {publisher})")
        except Exception:
            news_summary.append("- News unavailable at this moment.")

        news_str = "\n".join(news_summary) if news_summary else "No recent news found."

        if isinstance(profit_margins, (int, float)):
            profit_margin_str = f"{profit_margins * 100:.2f}%"
        else:
            profit_margin_str = "N/A"

        return (
            f"=== FINANCIAL DATA FOR {ticker_symbol} ===\n"
            f"Current Price: {current_price} {currency}\n"
            f"52-Week Range: {fifty_two_week_low} - {fifty_two_week_high}\n"
            f"Market Cap: {fmt_num(market_cap)}\n"
            f"P/E Ratio: {pe_ratio}\n\n"
            f"--- Financial Performance ---\n"
            f"Total Revenue: {fmt_num(total_revenue)}\n"
            f"Net Income: {fmt_num(net_income)}\n"
            f"Profit Margin: {profit_margin_str}\n\n"
            f"--- Analyst Viewpoints ---\n"
            f"Consensus Rating: {recommendation}\n"
            f"Average Target Price: {target_mean_price} {currency} (based on {num_analysts} analysts)\n\n"
            f"--- Recent Headlines ---\n"
            f"{news_str}\n"
        )

    except Exception as e:
        return f"Failed to retrieve stock information for '{symbol}': {str(e)}"
import yfinance as yf
from typing import Any


def get_stock_analysis(symbol: str) -> str:
    """
    Fetches real-time price, quarterly/annual financial health,
    analyst recommendations, and top news for a given stock ticker symbol.
    """
    try:
        ticker_symbol = (symbol or "").upper().strip()
        if not ticker_symbol:
            return "Error: No ticker symbol provided."

        ticker = yf.Ticker(ticker_symbol)
        info: Any = getattr(ticker, "info", {}) or {}

        # Fallbacks for modern yfinance which sometimes uses fast_info or raw attrs
        if not info:
            try:
                info = ticker.fast_info or {}
            except Exception:
                info = {}

        if not info or ("regularMarketPrice" not in info and "currentPrice" not in info and "last_price" not in info):
            return f"Error: Could not retrieve valid financial data for ticker '{symbol}'."

        # 1. Price & Valuations
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("last_price", "N/A")
        currency = info.get("currency", "USD")
        market_cap = info.get("marketCap", info.get("market_cap", 0))
        pe_ratio = info.get("trailingPE", info.get("pe_ratio", "N/A"))
        fifty_two_week_high = info.get("fiftyTwoWeekHigh", info.get("fifty_two_week_high", "N/A"))
        fifty_two_week_low = info.get("fiftyTwoWeekLow", info.get("fifty_two_week_low", "N/A"))

        # 2. Financial Metrics
        total_revenue = info.get("totalRevenue", info.get("total_revenue", 0))
        net_income = info.get("netIncomeToCommon", info.get("net_income", 0))
        profit_margins = info.get("profitMargins", info.get("profit_margins", None))

        def fmt_num(num):
            try:
                if isinstance(num, (int, float)) and num != 0:
                    if abs(num) >= 1e12:
                        return f"${num/1e12:.2f}T"
                    if abs(num) >= 1e9:
                        return f"${num/1e9:.2f}B"
                    if abs(num) >= 1e6:
                        return f"${num/1e6:.2f}M"
                return str(num)
            except Exception:
                return str(num)

        # 3. Analyst Viewpoints
        recommendation = str(info.get("recommendationKey", info.get("recommendation", "N/A"))).replace("_", " ").title()
        target_mean_price = info.get("targetMeanPrice", info.get("target_mean_price", "N/A"))
        num_analysts = info.get("numberOfAnalystOpinions", info.get("analyst_count", "N/A"))

        # 4. News Headlines
        news_summary = []
        try:
            raw_news = getattr(ticker, "news", []) or []
            for item in raw_news[:3]:
                title = item.get("title") or item.get("content", {}).get("title", "")
                publisher = item.get("publisher") or item.get("source") or item.get("content", {}).get("provider", {}).get("displayName", "")
                if title:
                    news_summary.append(f"- {title} (Source: {publisher})")
        except Exception:
            news_summary.append("- News unavailable at this moment.")

        news_str = "\n".join(news_summary) if news_summary else "No recent news found."

        if isinstance(profit_margins, (int, float)):
            profit_margin_str = f"{profit_margins * 100:.2f}%"
        else:
            profit_margin_str = "N/A"

        return (
            f"=== FINANCIAL DATA FOR {ticker_symbol} ===\n"
            f"Current Price: {current_price} {currency}\n"
            f"52-Week Range: {fifty_two_week_low} - {fifty_two_week_high}\n"
            f"Market Cap: {fmt_num(market_cap)}\n"
            f"P/E Ratio: {pe_ratio}\n\n"
            f"--- Financial Performance ---\n"
            f"Total Revenue: {fmt_num(total_revenue)}\n"
            f"Net Income: {fmt_num(net_income)}\n"
            f"Profit Margin: {profit_margin_str}\n\n"
            f"--- Analyst Viewpoints ---\n"
            f"Consensus Rating: {recommendation}\n"
            f"Average Target Price: {target_mean_price} {currency} (based on {num_analysts} analysts)\n\n"
            f"--- Recent Headlines ---\n"
            f"{news_str}\n"
        )

    except Exception as e:
        return f"Failed to retrieve stock information for '{symbol}': {str(e)}"
