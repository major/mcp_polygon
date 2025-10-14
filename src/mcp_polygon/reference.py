"""Reference data endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict, Union
from datetime import datetime, date
from mcp.types import ToolAnnotations

from .helpers import build_error_response


def register_tools(mcp_server, polygon_client):
    """Register reference data tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_tickers(
        ticker: Optional[str] = None,
        type: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        cusip: Optional[str] = None,
        cik: Optional[str] = None,
        date: Optional[Union[str, datetime, date]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        sort: Optional[str] = None,
        order: Optional[str] = "desc",
        limit: Optional[int] = 100,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search and list ticker symbols across all asset classes with flexible filtering.

        This is a powerful search tool for finding tickers by symbol, company name, type,
        exchange, or other identifiers. Returns detailed information about each ticker
        including name, market, type, and various identifiers. Perfect for ticker discovery
        and validation.

        Args:
            ticker: Filter by ticker symbol (exact match, e.g., "AAPL")
            type: Filter by ticker type - Options: "CS" (Common Stock), "ETF", "ADRC" (ADR Common),
                  "ADRP" (ADR Preferred), "FUND", "SP" (Structured Product), "WARRANT", "RIGHT", "BOND"
            market: Filter by market - Options: "stocks", "crypto", "fx", "otc", "indices"
            exchange: Filter by exchange code (e.g., "XNAS" for NASDAQ, "XNYS" for NYSE)
            cusip: Filter by CUSIP identifier (9-character alphanumeric security identifier)
            cik: Filter by SEC CIK number (Central Index Key for SEC filings)
            date: Get tickers as of specific date in YYYY-MM-DD format (e.g., "2024-01-15")
            search: Search by ticker symbol or company name (partial match, e.g., "Apple")
            active: Filter by active status - True for currently active tickers, False for delisted
            sort: Field to sort by (e.g., "ticker", "name", "market")
            order: Sort order - "asc" (A-Z) or "desc" (Z-A). Default: "desc"
            limit: Maximum number of results to return (default: 100, max: 1000)
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing ticker information:
            - ticker: Ticker symbol
            - name: Company/asset name
            - market: Market type (stocks, crypto, fx, etc.)
            - locale: Locale (us, global)
            - primary_exchange: Primary exchange code
            - type: Ticker type (CS, ETF, etc.)
            - active: Whether currently active
            - currency_name: Currency for trading
            - cik: SEC CIK number (if available)
            - composite_figi: FIGI identifier (if available)
            - share_class_figi: Share class FIGI (if available)

        Example Usage:
            - Search by name: list_tickers(search="Apple", limit=10)
            - Find all ETFs: list_tickers(type="ETF", active=True, limit=50)
            - Active stocks on NASDAQ: list_tickers(market="stocks", exchange="XNAS", active=True)

        Related Tools:
            - get_ticker_details: Get detailed information for a specific ticker
            - get_snapshot_ticker: Get real-time market data for a ticker
            - list_ticker_news: Get news articles for a ticker
        """
        try:
            results = polygon_client.list_tickers(
                ticker=ticker,
                type=type,
                market=market,
                exchange=exchange,
                cusip=cusip,
                cik=cik,
                date=date,
                search=search,
                active=active,
                sort=sort,
                order=order,
                limit=limit,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, "Listing tickers")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ticker_details(
        ticker: str,
        date: Optional[Union[str, datetime, date]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive details and metadata for a specific ticker symbol.

        This returns extensive information about a company or asset including business
        description, classification, market cap, share counts, contact information, and
        various identifiers. Essential for fundamental analysis and research.

        Args:
            ticker: Ticker symbol (e.g., "AAPL", "TSLA", "MSFT")
            date: Get ticker details as of specific date in YYYY-MM-DD format (e.g., "2024-01-15").
                  If not specified, returns current details.
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with comprehensive ticker details:
            - ticker: Ticker symbol
            - name: Company/asset full name
            - market: Market type (stocks, crypto, fx, etc.)
            - locale: Geographic locale
            - primary_exchange: Primary exchange code
            - type: Security type (CS, ETF, etc.)
            - active: Whether currently active/trading
            - currency_name: Trading currency
            - cik: SEC Central Index Key
            - composite_figi: Bloomberg FIGI identifier
            - share_class_figi: Share class FIGI
            - market_cap: Market capitalization
            - phone_number: Company phone number
            - address: Physical address (street, city, state, postal_code)
            - description: Business description
            - sic_code: Standard Industrial Classification code
            - sic_description: SIC description
            - ticker_root: Root ticker symbol
            - homepage_url: Company website
            - total_employees: Number of employees
            - list_date: Initial listing date
            - branding: Logo and icon URLs
            - share_class_shares_outstanding: Outstanding shares count
            - weighted_shares_outstanding: Weighted average shares

        Example Usage:
            - Get Apple details: get_ticker_details("AAPL")
            - Get historical details: get_ticker_details("TSLA", date="2023-01-01")
            - Get ETF details: get_ticker_details("SPY")

        Related Tools:
            - list_tickers: Search for tickers
            - get_snapshot_ticker: Get real-time market data
            - list_ticker_news: Get news articles for the ticker
            - list_stock_financials: Get financial statements and metrics
        """
        try:
            results = polygon_client.get_ticker_details(
                ticker=ticker, date=date, params=params, raw=True
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Getting details for ticker {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_ticker_news(
        ticker: Optional[str] = None,
        published_utc: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = 10,
        sort: Optional[str] = "published_utc",
        order: Optional[str] = "desc",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get recent news articles related to a specific ticker or market-wide news.

        This retrieves news articles from various publishers, including headlines, summaries,
        article URLs, publisher info, and related tickers. Perfect for staying informed about
        market-moving events, earnings, and company developments.

        Args:
            ticker: Filter news by ticker symbol (e.g., "AAPL", "TSLA"). If not specified, returns market-wide news.
            published_utc: Filter news published at or after this date/time.
                           Use YYYY-MM-DD format (e.g., "2024-01-15") or ISO 8601 datetime
            limit: Maximum number of articles to return (default: 10, max: 1000)
            sort: Field to sort by - Options: "published_utc" (default). Default: "published_utc"
            order: Sort order - "asc" (oldest first) or "desc" (newest first). Default: "desc"
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing news articles:
            - id: Unique article identifier
            - publisher: Publisher information (name, homepage_url, logo_url, favicon_url)
            - title: Article headline
            - author: Article author
            - published_utc: Publication timestamp (ISO 8601 format)
            - article_url: Link to full article
            - tickers: Array of related ticker symbols
            - amp_url: AMP version URL (if available)
            - image_url: Featured image URL
            - description: Article summary/excerpt
            - keywords: Array of article keywords
            - insights: AI-generated insights and sentiment (if available)

        Example Usage:
            - Latest Apple news: list_ticker_news("AAPL", limit=5)
            - Market news today: list_ticker_news(published_utc="2024-01-15", limit=20)
            - Older Tesla news: list_ticker_news("TSLA", order="asc", limit=10)

        Related Tools:
            - get_ticker_details: Get company details and description
            - get_snapshot_ticker: Get real-time market data
            - list_tickers: Search for ticker symbols
        """
        try:
            results = polygon_client.list_ticker_news(
                ticker=ticker,
                published_utc=published_utc,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(
                e, f"Listing news for {ticker if ticker else 'market'}"
            )

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ticker_types(
        asset_class: Optional[str] = None,
        locale: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List all ticker types supported by Polygon.io.
        """
        try:
            results = polygon_client.get_ticker_types(
                asset_class=asset_class, locale=locale, params=params, raw=True
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_conditions(
        asset_class: Optional[str] = None,
        data_type: Optional[str] = None,
        id: Optional[int] = None,
        sip: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List conditions used by Polygon.io.
        """
        try:
            results = polygon_client.list_conditions(
                asset_class=asset_class,
                data_type=data_type,
                id=id,
                sip=sip,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchanges(
        asset_class: Optional[str] = None,
        locale: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List exchanges known by Polygon.io.
        """
        try:
            results = polygon_client.get_exchanges(
                asset_class=asset_class, locale=locale, params=params, raw=True
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    # Simplified wrapper tools
    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_news_recent(
        ticker: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get recent news articles for a stock or the overall market (simplified).

        Easy way to get the latest news. Omit ticker for general market news, or
        specify a ticker for company-specific news.

        Args:
            ticker: Stock symbol for company-specific news (e.g., "AAPL"), or None for market news
            limit: Number of articles to return (default: 10, max: 50)

        Returns:
            JSON array of news articles with title, description, publisher, URL, timestamp

        Example Usage:
            - get_stock_news_recent("AAPL", 5) - Latest 5 Apple news articles
            - get_stock_news_recent() - Latest 10 general market news
            - get_stock_news_recent("TSLA", 20) - Latest 20 Tesla articles

        Related Tools:
            - list_ticker_news: More control over date ranges and filters
            - get_ticker_details: Company information and fundamentals
        """
        try:
            return await list_ticker_news(
                ticker=ticker, limit=limit, sort="published_utc", order="desc"
            )
        except Exception as e:
            context = f"Getting news for {ticker}" if ticker else "Getting market news"
            return build_error_response(e, context)

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_company_info(ticker: str) -> Dict[str, Any]:
        """
        Get detailed company information and fundamentals (simplified).

        One call to get comprehensive company metadata including description, industry,
        market cap, employee count, website, and more.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")

        Returns:
            JSON with extensive company details including:
            - Name and description
            - Industry and sector
            - Market cap and share count
            - Contact info (website, phone, address)
            - Trading details (primary exchange, currency)
            - Branding (logo URLs, colors)

        Example Usage:
            - get_company_info("AAPL")
            - get_company_info("GOOGL")
            - get_company_info("TSLA")

        Related Tools:
            - get_ticker_details: The underlying API this uses
            - list_stock_financials: Financial statements
            - list_ticker_news: Company news
        """
        try:
            return await get_ticker_details(ticker=ticker)
        except Exception as e:
            return build_error_response(e, f"Getting company info for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def search_stocks(search_term: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for stocks by company name or ticker (simplified).

        Easy way to find tickers when you know the company name but not the symbol.
        Searches across company names and ticker symbols.

        Args:
            search_term: Company name or partial ticker to search for (e.g., "Apple", "Tesla", "Micro")
            limit: Maximum number of results to return (default: 10, max: 100)

        Returns:
            JSON array of matching tickers with name, symbol, type, market, and other details

        Example Usage:
            - search_stocks("Apple") - Find Apple Inc.
            - search_stocks("Tesla", 5) - Find Tesla and related
            - search_stocks("tech") - Find companies with "tech" in name

        Related Tools:
            - list_tickers: The underlying API this uses (with more filter options)
            - get_ticker_details: Get full details after finding ticker
        """
        try:
            return await list_tickers(
                search=search_term, active=True, limit=limit, order="desc"
            )
        except Exception as e:
            return build_error_response(e, f"Searching for '{search_term}'")
