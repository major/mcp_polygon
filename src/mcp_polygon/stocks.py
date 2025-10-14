"""Stock-related endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict, Union, List
from datetime import datetime, date
from mcp.types import ToolAnnotations

from .helpers import build_error_response, get_date_range_default


def register_tools(mcp_server, polygon_client):
    """Register stock-related tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_aggs(
        ticker: str,
        multiplier: int,
        timespan: str,
        from_: Union[str, int, datetime, date],
        to: Union[str, int, datetime, date],
        adjusted: Optional[bool] = True,
        sort: Optional[str] = "desc",
        limit: Optional[int] = 5000,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregate bars (OHLCV data) for a stock/crypto ticker over a date range.

        This returns Open, High, Low, Close, and Volume data aggregated over custom time windows.
        Perfect for historical price analysis, charting, and backtesting.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA") or crypto pair (e.g., "X:BTCUSD")
            multiplier: Size of the time window (e.g., 1, 5, 15, 60)
            timespan: Time unit for the window - Options: "minute", "hour", "day", "week", "month", "quarter", "year"
            from_: Start date - Use YYYY-MM-DD format (e.g., "2024-01-01"), datetime object, or Unix timestamp
            to: End date - Use YYYY-MM-DD format (e.g., "2024-12-31"), datetime object, or Unix timestamp
            adjusted: Whether to adjust for splits/dividends (True = split-adjusted prices, recommended for accuracy)
            sort: Sort order - "asc" (oldest first) or "desc" (newest first)
            limit: Maximum number of results to return (default: 5000, max: 50000)
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing aggregate bars, each with:
            - o: Open price
            - h: High price
            - l: Low price
            - c: Close price
            - v: Volume
            - t: Timestamp (Unix milliseconds)

        Example Usage:
            - Daily bars: get_aggs("AAPL", 1, "day", "2024-01-01", "2024-01-31")
            - 5-minute bars: get_aggs("TSLA", 5, "minute", "2024-01-15", "2024-01-15")
            - Weekly bars: get_aggs("MSFT", 1, "week", "2023-01-01", "2024-01-01")

        Related Tools:
            - list_aggs: Same as get_aggs but returns an iterator for large datasets
            - get_daily_open_close_agg: Get single day's OHLC for a specific date
            - get_previous_close_agg: Get previous trading day's OHLC
        """
        try:
            results = polygon_client.get_aggs(
                ticker=ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_,
                to=to,
                adjusted=adjusted,
                sort=sort,
                limit=limit,
                params=params,
                raw=True,
            )

            # Parse the binary data to string and then to JSON
            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Getting aggregates for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_aggs(
        ticker: str,
        multiplier: int,
        timespan: str,
        from_: Union[str, int, datetime, date],
        to: Union[str, int, datetime, date],
        adjusted: Optional[bool] = True,
        sort: Optional[str] = "desc",
        limit: Optional[int] = 5000,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List aggregate bars (OHLCV data) for a stock/crypto ticker as an iterator.

        This is similar to get_aggs but optimized for handling large datasets by returning
        results as an iterator. Ideal for processing historical data in chunks or when you
        need to handle datasets that might exceed memory limits.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA") or crypto pair (e.g., "X:BTCUSD")
            multiplier: Size of the time window (e.g., 1, 5, 15, 60)
            timespan: Time unit for the window - Options: "minute", "hour", "day", "week", "month", "quarter", "year"
            from_: Start date - Use YYYY-MM-DD format (e.g., "2024-01-01"), datetime object, or Unix timestamp
            to: End date - Use YYYY-MM-DD format (e.g., "2024-12-31"), datetime object, or Unix timestamp
            adjusted: Whether to adjust for splits/dividends (True = split-adjusted prices, recommended for accuracy). Default: True
            sort: Sort order - "asc" (oldest first) or "desc" (newest first). Default: "desc"
            limit: Maximum number of results to return (default: 5000, max: 50000)
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing aggregate bars, each with:
            - o: Open price
            - h: High price
            - l: Low price
            - c: Close price
            - v: Volume
            - t: Timestamp (Unix milliseconds)
            - vw: Volume weighted average price (if available)
            - n: Number of transactions (if available)

        Example Usage:
            - Daily bars for year: list_aggs("AAPL", 1, "day", "2024-01-01", "2024-12-31")
            - Hourly bars: list_aggs("TSLA", 1, "hour", "2024-01-01", "2024-01-31")
            - Monthly bars: list_aggs("MSFT", 1, "month", "2020-01-01", "2024-01-01")

        Related Tools:
            - get_aggs: Non-iterator version for smaller datasets
            - get_daily_open_close_agg: Get single day's OHLC for a specific date
            - get_previous_close_agg: Get previous trading day's OHLC
        """
        try:
            results = polygon_client.list_aggs(
                ticker=ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_,
                to=to,
                adjusted=adjusted,
                sort=sort,
                limit=limit,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Listing aggregates for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_grouped_daily_aggs(
        date: str,
        adjusted: Optional[bool] = None,
        include_otc: Optional[bool] = None,
        locale: Optional[str] = None,
        market_type: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get grouped daily bars for entire market for a specific date.
        """
        try:
            results = polygon_client.get_grouped_daily_aggs(
                date=date,
                adjusted=adjusted,
                include_otc=include_otc,
                locale=locale,
                market_type=market_type,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_daily_open_close_agg(
        ticker: str,
        date: str,
        adjusted: Optional[bool] = True,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get the OHLC (Open, High, Low, Close) data for a specific ticker on a specific date.

        This returns a snapshot of a ticker's trading activity for a single day, including
        opening price, high, low, closing price, volume, and other key metrics. Perfect for
        getting detailed daily statistics for a specific historical date.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "GOOGL")
            date: Trading date in YYYY-MM-DD format (e.g., "2024-01-15", "2024-12-31")
            adjusted: Whether to adjust for splits/dividends (True = split-adjusted prices, recommended). Default: True
            params: Additional query parameters as a dictionary

        Returns:
            JSON response containing:
            - symbol: Ticker symbol
            - open: Opening price
            - high: Highest price during the day
            - low: Lowest price during the day
            - close: Closing price
            - volume: Total trading volume
            - afterHours: After-hours trading price (if available)
            - preMarket: Pre-market trading price (if available)

        Example Usage:
            - Get Apple's data for specific date: get_daily_open_close_agg("AAPL", "2024-01-15")
            - Get Tesla's data: get_daily_open_close_agg("TSLA", "2024-03-20")
            - Unadjusted data: get_daily_open_close_agg("MSFT", "2024-01-15", adjusted=False)

        Related Tools:
            - get_previous_close_agg: Get previous trading day's OHLC
            - get_aggs: Get OHLC data for a date range
            - list_aggs: Iterator version for large datasets
        """
        try:
            results = polygon_client.get_daily_open_close_agg(
                ticker=ticker, date=date, adjusted=adjusted, params=params, raw=True
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Getting daily OHLC for {ticker} on {date}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_previous_close_agg(
        ticker: str,
        adjusted: Optional[bool] = True,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get the previous trading day's OHLC data for a specific ticker.

        This retrieves the most recent completed trading day's open, high, low, close, and volume
        data. Useful for getting the latest daily snapshot without needing to specify a date.
        Automatically handles weekends and market holidays.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")
            adjusted: Whether to adjust for splits/dividends (True = split-adjusted prices, recommended). Default: True
            params: Additional query parameters as a dictionary

        Returns:
            JSON response containing:
            - T: Ticker symbol
            - o: Opening price
            - h: Highest price during the day
            - l: Lowest price during the day
            - c: Closing price
            - v: Total trading volume
            - vw: Volume weighted average price
            - t: Timestamp (Unix milliseconds)

        Example Usage:
            - Get Apple's previous close: get_previous_close_agg("AAPL")
            - Get Tesla's previous close: get_previous_close_agg("TSLA")
            - Unadjusted data: get_previous_close_agg("MSFT", adjusted=False)

        Related Tools:
            - get_daily_open_close_agg: Get OHLC for a specific date
            - get_aggs: Get OHLC data for a date range
            - get_snapshot_ticker: Get real-time snapshot with current price
        """
        try:
            results = polygon_client.get_previous_close_agg(
                ticker=ticker, adjusted=adjusted, params=params, raw=True
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Getting previous close for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_trades(
        ticker: str,
        timestamp: Optional[Union[str, int, datetime, date]] = None,
        timestamp_lt: Optional[Union[str, int, datetime, date]] = None,
        timestamp_lte: Optional[Union[str, int, datetime, date]] = None,
        timestamp_gt: Optional[Union[str, int, datetime, date]] = None,
        timestamp_gte: Optional[Union[str, int, datetime, date]] = None,
        limit: Optional[int] = 100,
        sort: Optional[str] = None,
        order: Optional[str] = "desc",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List individual trades for a ticker symbol with detailed execution information.

        This returns the tick-by-tick trade data showing every individual trade execution,
        including price, size, exchange, and timestamp. Perfect for detailed trade analysis,
        order flow studies, and high-frequency data analysis.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")
            timestamp: Exact timestamp for trades - Use YYYY-MM-DD format, datetime object, or Unix timestamp (nanoseconds)
            timestamp_lt: Get trades before this timestamp (less than)
            timestamp_lte: Get trades before or at this timestamp (less than or equal)
            timestamp_gt: Get trades after this timestamp (greater than)
            timestamp_gte: Get trades after or at this timestamp (greater than or equal)
            limit: Maximum number of trades to return (default: 100, max: 50000)
            sort: Field to sort by (e.g., "timestamp")
            order: Sort order - "asc" (oldest first) or "desc" (newest first). Default: "desc"
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing individual trades, each with:
            - t: Timestamp (nanoseconds)
            - y: Exchange timestamp
            - f: TRF timestamp
            - q: Sequence number
            - i: Trade ID
            - x: Exchange code
            - s: Trade size (shares)
            - c: Trade conditions
            - p: Trade price
            - z: Tape (which SIP feed)

        Example Usage:
            - Recent trades: list_trades("AAPL", limit=50)
            - Trades on specific date: list_trades("TSLA", timestamp_gte="2024-01-15", timestamp_lt="2024-01-16")
            - Oldest first: list_trades("MSFT", limit=100, order="asc")

        Related Tools:
            - get_last_trade: Get only the most recent trade
            - list_quotes: Get bid/ask quotes instead of trades
            - get_last_quote: Get most recent quote
        """
        try:
            results = polygon_client.list_trades(
                ticker=ticker,
                timestamp=timestamp,
                timestamp_lt=timestamp_lt,
                timestamp_lte=timestamp_lte,
                timestamp_gt=timestamp_gt,
                timestamp_gte=timestamp_gte,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Listing trades for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_last_trade(
        ticker: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get the most recent trade execution for a ticker symbol.

        This retrieves the very latest trade that occurred for a stock, providing real-time
        or near-real-time trade information including price, size, exchange, and exact timestamp.
        Ideal for checking the last traded price and volume.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")
            params: Additional query parameters as a dictionary

        Returns:
            JSON response containing the last trade with:
            - T: Ticker symbol
            - t: Timestamp (nanoseconds)
            - y: Exchange timestamp
            - f: TRF timestamp
            - q: Sequence number
            - i: Trade ID
            - x: Exchange code where trade occurred
            - s: Trade size (number of shares)
            - c: Array of trade conditions/flags
            - p: Trade price
            - z: Tape (which SIP feed: 1=A, 2=B, 3=C)

        Example Usage:
            - Get last Apple trade: get_last_trade("AAPL")
            - Get last Tesla trade: get_last_trade("TSLA")
            - Get last Microsoft trade: get_last_trade("MSFT")

        Related Tools:
            - list_trades: Get multiple trades with filtering
            - get_last_quote: Get most recent bid/ask quote
            - get_snapshot_ticker: Get comprehensive snapshot including last trade
        """
        try:
            results = polygon_client.get_last_trade(ticker=ticker, params=params, raw=True)

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Getting last trade for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_quotes(
        ticker: str,
        timestamp: Optional[Union[str, int, datetime, date]] = None,
        timestamp_lt: Optional[Union[str, int, datetime, date]] = None,
        timestamp_lte: Optional[Union[str, int, datetime, date]] = None,
        timestamp_gt: Optional[Union[str, int, datetime, date]] = None,
        timestamp_gte: Optional[Union[str, int, datetime, date]] = None,
        limit: Optional[int] = 100,
        sort: Optional[str] = None,
        order: Optional[str] = "desc",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List NBBO quotes for a ticker symbol with bid/ask pricing over time.

        This returns historical tick-by-tick quote data showing the National Best Bid and Offer
        (NBBO) at different points in time. Each quote shows what buyers were willing to pay
        (bid) and what sellers were asking (ask). Perfect for analyzing spread patterns,
        liquidity, and order book dynamics.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")
            timestamp: Exact timestamp for quotes - Use YYYY-MM-DD format, datetime object, or Unix timestamp (nanoseconds)
            timestamp_lt: Get quotes before this timestamp (less than)
            timestamp_lte: Get quotes before or at this timestamp (less than or equal)
            timestamp_gt: Get quotes after this timestamp (greater than)
            timestamp_gte: Get quotes after or at this timestamp (greater than or equal)
            limit: Maximum number of quotes to return (default: 100, max: 50000)
            sort: Field to sort by (e.g., "timestamp")
            order: Sort order - "asc" (oldest first) or "desc" (newest first). Default: "desc"
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing quotes, each with:
            - t: Timestamp (nanoseconds)
            - y: Exchange timestamp
            - f: TRF timestamp
            - q: Sequence number
            - x: Bid exchange code
            - X: Ask exchange code
            - p: Bid price
            - P: Ask price
            - s: Bid size (shares)
            - S: Ask size (shares)
            - c: Quote conditions/flags
            - i: Indicators
            - z: Tape (which SIP feed)

        Example Usage:
            - Recent quotes: list_quotes("AAPL", limit=50)
            - Quotes on specific date: list_quotes("TSLA", timestamp_gte="2024-01-15", timestamp_lt="2024-01-16")
            - Oldest first: list_quotes("MSFT", limit=100, order="asc")

        Related Tools:
            - get_last_quote: Get only the most recent quote
            - list_trades: Get trade executions instead of quotes
            - get_last_trade: Get most recent trade
        """
        try:
            results = polygon_client.list_quotes(
                ticker=ticker,
                timestamp=timestamp,
                timestamp_lt=timestamp_lt,
                timestamp_lte=timestamp_lte,
                timestamp_gt=timestamp_gt,
                timestamp_gte=timestamp_gte,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Listing quotes for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_last_quote(
        ticker: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get the most recent NBBO (National Best Bid and Offer) quote for a ticker.

        This retrieves the latest bid/ask quote showing what buyers are willing to pay and
        what sellers are asking. The NBBO represents the best available prices across all
        exchanges. Perfect for checking current market sentiment and spread.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")
            params: Additional query parameters as a dictionary

        Returns:
            JSON response containing the last quote with:
            - T: Ticker symbol
            - t: Timestamp (nanoseconds)
            - y: Exchange timestamp
            - f: TRF timestamp
            - q: Sequence number
            - i: Indicator/quote condition
            - x: Bid exchange code
            - X: Ask exchange code
            - p: Bid price
            - P: Ask price
            - s: Bid size (shares)
            - S: Ask size (shares)
            - c: Quote conditions/flags
            - z: Tape (which SIP feed)

        Example Usage:
            - Get current Apple bid/ask: get_last_quote("AAPL")
            - Get Tesla quote: get_last_quote("TSLA")
            - Get Microsoft quote: get_last_quote("MSFT")

        Related Tools:
            - list_quotes: Get multiple historical quotes
            - get_last_trade: Get most recent trade execution
            - get_snapshot_ticker: Get comprehensive snapshot including quote
        """
        try:
            results = polygon_client.get_last_quote(ticker=ticker, params=params, raw=True)

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(e, f"Getting last quote for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_universal_snapshots(
        type: str,
        ticker_any_of: Optional[List[str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get universal snapshots for multiple assets of a specific type.
        """
        try:
            results = polygon_client.list_universal_snapshots(
                type=type,
                ticker_any_of=ticker_any_of,
                order=order,
                limit=limit,
                sort=sort,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_snapshot_all(
        market_type: str,
        tickers: Optional[List[str]] = None,
        include_otc: Optional[bool] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get a snapshot of all tickers in a market.
        """
        try:
            results = polygon_client.get_snapshot_all(
                market_type=market_type,
                tickers=tickers,
                include_otc=include_otc,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_snapshot_direction(
        market_type: str,
        direction: str,
        include_otc: Optional[bool] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get gainers or losers for a market.
        """
        try:
            results = polygon_client.get_snapshot_direction(
                market_type=market_type,
                direction=direction,
                include_otc=include_otc,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_snapshot_ticker(
        market_type: str,
        ticker: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get a real-time snapshot of current market data for a specific ticker.

        This provides a comprehensive view of a ticker's current state, combining the latest
        trade, quote, minute bar, and daily bar into a single response. Perfect for getting
        a complete picture of a security's current market activity all at once.

        Args:
            market_type: Type of market - Options: "stocks", "crypto", "forex", "otc", "indices"
            ticker: Ticker symbol - Format depends on market_type:
                    - Stocks: "AAPL", "TSLA", "MSFT"
                    - Crypto: "X:BTCUSD", "X:ETHUSD"
                    - Forex: "C:EURUSD", "C:USDJPY"
                    - Indices: "I:SPX", "I:DJI"
            params: Additional query parameters as a dictionary

        Returns:
            JSON response containing comprehensive snapshot data:
            - ticker: The ticker symbol
            - todaysChange: Dollar change from previous close
            - todaysChangePerc: Percentage change from previous close
            - updated: Last update timestamp (nanoseconds)
            - day: Today's aggregated data (open, high, low, close, volume, vwap)
            - min: Latest minute bar data
            - prevDay: Previous day's aggregated data
            - lastTrade: Most recent trade details (price, size, timestamp, exchange)
            - lastQuote: Most recent NBBO quote (bid, ask, bidSize, askSize)

        Example Usage:
            - Stock snapshot: get_snapshot_ticker("stocks", "AAPL")
            - Crypto snapshot: get_snapshot_ticker("crypto", "X:BTCUSD")
            - Forex snapshot: get_snapshot_ticker("forex", "C:EURUSD")

        Related Tools:
            - get_last_trade: Get only the last trade
            - get_last_quote: Get only the last quote
            - get_previous_close_agg: Get previous day's OHLC
            - get_snapshot_all: Get snapshots for all tickers in a market
        """
        try:
            results = polygon_client.get_snapshot_ticker(
                market_type=market_type, ticker=ticker, params=params, raw=True
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(
                e, f"Getting snapshot for {ticker} in {market_type} market"
            )

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_stock_financials(
        ticker: Optional[str] = None,
        cik: Optional[str] = None,
        company_name: Optional[str] = None,
        company_name_search: Optional[str] = None,
        sic: Optional[str] = None,
        filing_date: Optional[Union[str, datetime, date]] = None,
        filing_date_lt: Optional[Union[str, datetime, date]] = None,
        filing_date_lte: Optional[Union[str, datetime, date]] = None,
        filing_date_gt: Optional[Union[str, datetime, date]] = None,
        filing_date_gte: Optional[Union[str, datetime, date]] = None,
        period_of_report_date: Optional[Union[str, datetime, date]] = None,
        period_of_report_date_lt: Optional[Union[str, datetime, date]] = None,
        period_of_report_date_lte: Optional[Union[str, datetime, date]] = None,
        period_of_report_date_gt: Optional[Union[str, datetime, date]] = None,
        period_of_report_date_gte: Optional[Union[str, datetime, date]] = None,
        timeframe: Optional[str] = None,
        include_sources: Optional[bool] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get fundamental financial data for companies.
        """
        try:
            results = polygon_client.vx.list_stock_financials(
                ticker=ticker,
                cik=cik,
                company_name=company_name,
                company_name_search=company_name_search,
                sic=sic,
                filing_date=filing_date,
                filing_date_lt=filing_date_lt,
                filing_date_lte=filing_date_lte,
                filing_date_gt=filing_date_gt,
                filing_date_gte=filing_date_gte,
                period_of_report_date=period_of_report_date,
                period_of_report_date_lt=period_of_report_date_lt,
                period_of_report_date_lte=period_of_report_date_lte,
                period_of_report_date_gt=period_of_report_date_gt,
                period_of_report_date_gte=period_of_report_date_gte,
                timeframe=timeframe,
                include_sources=include_sources,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_splits(
        ticker: Optional[str] = None,
        execution_date: Optional[Union[str, datetime, date]] = None,
        reverse_split: Optional[bool] = None,
        limit: Optional[int] = 100,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get historical stock split events for analyzing share dilution and consolidation.

        This retrieves stock split data showing when companies split (or reverse split) their
        shares, including the split ratio and execution date. Essential for understanding
        historical price adjustments and share count changes.

        Args:
            ticker: Filter by ticker symbol (e.g., "AAPL", "TSLA", "GOOGL"). If not specified, returns all splits.
            execution_date: Filter by execution date in YYYY-MM-DD format (e.g., "2024-01-15").
                            Returns splits executed on or after this date.
            reverse_split: Filter by split type - True for reverse splits (consolidation),
                           False for forward splits (dilution), None for all splits
            limit: Maximum number of splits to return (default: 100)
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing split information:
            - ticker: Ticker symbol
            - execution_date: Date split was executed (YYYY-MM-DD format)
            - split_from: Pre-split share count (numerator)
            - split_to: Post-split share count (denominator)
            - ratio: Split ratio (split_to / split_from)

            Note: A 2-for-1 split means split_from=1, split_to=2 (each share becomes 2 shares)
                  A 1-for-2 reverse split means split_from=2, split_to=1 (every 2 shares become 1)

        Example Usage:
            - Apple's splits: list_splits("AAPL")
            - Recent splits: list_splits(execution_date="2024-01-01", limit=50)
            - Only reverse splits: list_splits(reverse_split=True, limit=25)

        Related Tools:
            - list_dividends: Get dividend payment history
            - get_ticker_details: Get comprehensive ticker information
            - get_aggs: Get price data (use adjusted=True to account for splits)
        """
        try:
            results = polygon_client.list_splits(
                ticker=ticker,
                execution_date=execution_date,
                reverse_split=reverse_split,
                limit=limit,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(
                e, f"Listing splits{' for ' + ticker if ticker else ''}"
            )

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_dividends(
        ticker: Optional[str] = None,
        ex_dividend_date: Optional[Union[str, datetime, date]] = None,
        frequency: Optional[int] = None,
        dividend_type: Optional[str] = None,
        limit: Optional[int] = 100,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get historical cash dividend payments for income analysis and yield calculations.

        This retrieves dividend distribution data including payment amounts, ex-dividend dates,
        payment dates, and dividend frequency. Essential for analyzing dividend history,
        calculating yields, and tracking income-generating investments.

        Args:
            ticker: Filter by ticker symbol (e.g., "AAPL", "MSFT", "JNJ"). If not specified, returns all dividends.
            ex_dividend_date: Filter by ex-dividend date in YYYY-MM-DD format (e.g., "2024-01-15").
                              Returns dividends with ex-date on or after this date.
                              (Ex-dividend date is when stock starts trading without dividend rights)
            frequency: Filter by payment frequency - Options:
                       0 = One-time/special dividend
                       1 = Annual (once per year)
                       2 = Semi-annual (twice per year)
                       4 = Quarterly (four times per year)
                       12 = Monthly (twelve times per year)
            dividend_type: Filter by dividend type - Options:
                           "CD" = Cash dividend (most common)
                           "SC" = Stock dividend
                           "LT" = Long-term capital gains
                           "ST" = Short-term capital gains
            limit: Maximum number of dividends to return (default: 100)
            params: Additional query parameters as a dictionary

        Returns:
            JSON response with results array containing dividend information:
            - ticker: Ticker symbol
            - cash_amount: Dividend amount per share (in USD)
            - declaration_date: Date dividend was announced (YYYY-MM-DD)
            - ex_dividend_date: Ex-dividend date - must own stock before this date (YYYY-MM-DD)
            - record_date: Record date - must be shareholder on this date (YYYY-MM-DD)
            - pay_date: Payment date - when dividend is paid (YYYY-MM-DD)
            - frequency: Payment frequency (0, 1, 2, 4, or 12)
            - dividend_type: Type of dividend (CD, SC, LT, ST)

        Example Usage:
            - Apple's dividends: list_dividends("AAPL", limit=20)
            - Recent quarterly dividends: list_dividends(frequency=4, ex_dividend_date="2024-01-01")
            - Microsoft dividend history: list_dividends("MSFT", limit=50)

        Related Tools:
            - list_splits: Get stock split history
            - get_ticker_details: Get comprehensive ticker information
            - get_aggs: Get price data (use adjusted=True to account for dividends)
        """
        try:
            results = polygon_client.list_dividends(
                ticker=ticker,
                ex_dividend_date=ex_dividend_date,
                frequency=frequency,
                dividend_type=dividend_type,
                limit=limit,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return build_error_response(
                e, f"Listing dividends{' for ' + ticker if ticker else ''}"
            )

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_ipos(
        ticker: Optional[str] = None,
        listing_date: Optional[Union[str, datetime, date]] = None,
        listing_date_lt: Optional[Union[str, datetime, date]] = None,
        listing_date_lte: Optional[Union[str, datetime, date]] = None,
        listing_date_gt: Optional[Union[str, datetime, date]] = None,
        listing_date_gte: Optional[Union[str, datetime, date]] = None,
        ipo_status: Optional[str] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve upcoming or historical IPOs.
        """
        try:
            results = polygon_client.vx.list_ipos(
                ticker=ticker,
                listing_date=listing_date,
                listing_date_lt=listing_date_lt,
                listing_date_lte=listing_date_lte,
                listing_date_gt=listing_date_gt,
                listing_date_gte=listing_date_gte,
                ipo_status=ipo_status,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_short_interest(
        ticker: Optional[str] = None,
        settlement_date: Optional[Union[str, datetime, date]] = None,
        settlement_date_lt: Optional[Union[str, datetime, date]] = None,
        settlement_date_lte: Optional[Union[str, datetime, date]] = None,
        settlement_date_gt: Optional[Union[str, datetime, date]] = None,
        settlement_date_gte: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve short interest data for stocks.
        """
        try:
            results = polygon_client.list_short_interest(
                ticker=ticker,
                settlement_date=settlement_date,
                settlement_date_lt=settlement_date_lt,
                settlement_date_lte=settlement_date_lte,
                settlement_date_gt=settlement_date_gt,
                settlement_date_gte=settlement_date_gte,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_short_volume(
        ticker: Optional[str] = None,
        date: Optional[Union[str, datetime, date]] = None,
        date_lt: Optional[Union[str, datetime, date]] = None,
        date_lte: Optional[Union[str, datetime, date]] = None,
        date_gt: Optional[Union[str, datetime, date]] = None,
        date_gte: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve short volume data for stocks.
        """
        try:
            results = polygon_client.list_short_volume(
                ticker=ticker,
                date=date,
                date_lt=date_lt,
                date_lte=date_lte,
                date_gt=date_gt,
                date_gte=date_gte,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_treasury_yields(
        date: Optional[Union[str, datetime, date]] = None,
        date_any_of: Optional[str] = None,
        date_lt: Optional[Union[str, datetime, date]] = None,
        date_lte: Optional[Union[str, datetime, date]] = None,
        date_gt: Optional[Union[str, datetime, date]] = None,
        date_gte: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve treasury yield data.
        """
        try:
            results = polygon_client.list_treasury_yields(
                date=date,
                date_lt=date_lt,
                date_lte=date_lte,
                date_gt=date_gt,
                date_gte=date_gte,
                limit=limit,
                sort=sort,
                order=order,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def list_inflation(
        date: Optional[Union[str, datetime, date]] = None,
        date_any_of: Optional[str] = None,
        date_gt: Optional[Union[str, datetime, date]] = None,
        date_gte: Optional[Union[str, datetime, date]] = None,
        date_lt: Optional[Union[str, datetime, date]] = None,
        date_lte: Optional[Union[str, datetime, date]] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get inflation data from the Federal Reserve.
        """
        try:
            results = polygon_client.list_inflation(
                date=date,
                date_any_of=date_any_of,
                date_gt=date_gt,
                date_gte=date_gte,
                date_lt=date_lt,
                date_lte=date_lte,
                limit=limit,
                sort=sort,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_related_companies(
        ticker: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get a list of tickers related to the queried ticker based on News and Returns data.
        """
        try:
            results = polygon_client.get_related_companies(
                ticker=ticker,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ticker_events(
        ticker: str,
        types: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get event history for a ticker (name changes, mergers, ticker changes, etc.).
        """
        try:
            results = polygon_client.get_ticker_events(
                ticker=ticker,
                types=types,
                params=params,
                raw=True,
            )

            data_str = results.data.decode("utf-8")
            return json.loads(data_str)
        except Exception as e:
            return {"error": str(e)}

    # Simplified wrapper tools
    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_latest_stock_price(ticker: str) -> Dict[str, Any]:
        """
        Get the current/latest price for a stock ticker (simplified).

        This is the easiest way to get a stock's current price. Returns the most recent
        trade data including price, volume, and timestamp.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")

        Returns:
            JSON with latest trade info including price, size, timestamp, and conditions

        Example Usage:
            - get_latest_stock_price("AAPL")
            - get_latest_stock_price("GOOGL")
            - get_latest_stock_price("NVDA")

        Related Tools:
            - get_last_trade: The underlying API this uses
            - get_simple_quote: Get bid/ask spread instead of last trade
            - get_snapshot_ticker: Get complete market snapshot
        """
        try:
            return await get_last_trade(ticker=ticker)
        except Exception as e:
            return build_error_response(e, f"Getting latest price for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_daily_bars(ticker: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get recent daily price bars for a stock (simplified).

        Returns daily OHLCV data for the last N days. Perfect for quick price history
        and trend analysis without needing to specify exact dates.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")
            days_back: Number of days of history to retrieve (default: 30, max: 365)

        Returns:
            JSON with array of daily bars, each containing open, high, low, close, volume

        Example Usage:
            - get_stock_daily_bars("AAPL") - Last 30 days
            - get_stock_daily_bars("TSLA", 90) - Last 90 days
            - get_stock_daily_bars("MSFT", 7) - Last week

        Related Tools:
            - get_aggs: More control over time ranges and intervals
            - get_previous_close_agg: Just yesterday's data
            - get_daily_open_close_agg: Specific single day
        """
        try:
            # Cap at 365 days
            days_back = min(days_back, 365)
            from_date, to_date = get_date_range_default(days_back)

            return await get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=from_date,
                to=to_date,
                adjusted=True,
                sort="desc",
                limit=days_back,
            )
        except Exception as e:
            return build_error_response(e, f"Getting daily bars for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_market_movers(
        direction: str = "gainers", limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get top market gainers or losers for the day (simplified).

        Quick way to see which stocks are moving the most. Great for market overview
        and identifying trading opportunities.

        Args:
            direction: Which movers to get - Options: "gainers" (up) or "losers" (down)
            limit: Number of results to return (default: 20, max: 250)

        Returns:
            JSON with snapshot data sorted by percent change, showing biggest movers

        Example Usage:
            - get_market_movers("gainers") - Top 20 gainers
            - get_market_movers("losers", 10) - Top 10 losers
            - get_market_movers("gainers", 50) - Top 50 gainers

        Related Tools:
            - get_snapshot_direction: The underlying API this uses
            - get_snapshot_all: All stock snapshots
            - get_grouped_daily_aggs: Full market daily data
        """
        try:
            return await get_snapshot_direction(
                market_type="stocks", direction=direction, include_otc=False, params={"limit": limit}
            )
        except Exception as e:
            return build_error_response(e, f"Getting market {direction}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_simple_quote(ticker: str) -> Dict[str, Any]:
        """
        Get current bid/ask quote for a stock (simplified).

        Quick way to see the current bid/ask spread and market depth. Shows what
        buyers are willing to pay (bid) and what sellers are asking (ask).

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")

        Returns:
            JSON with bid price, ask price, bid size, ask size, and timestamp

        Example Usage:
            - get_simple_quote("AAPL")
            - get_simple_quote("GOOGL")
            - get_simple_quote("MSFT")

        Related Tools:
            - get_last_quote: The underlying API this uses
            - get_latest_stock_price: Get last trade instead of quote
            - list_quotes: Historical quotes over time
        """
        try:
            return await get_last_quote(ticker=ticker)
        except Exception as e:
            return build_error_response(e, f"Getting quote for {ticker}")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_snapshot(ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive current market snapshot for a stock (simplified).

        One call to get everything: current price, today's OHLCV, previous day's data,
        current quote, and more. Perfect for a complete overview of a stock's status.

        Args:
            ticker: Stock symbol (e.g., "AAPL", "TSLA", "MSFT")

        Returns:
            JSON with complete snapshot including:
            - Latest trade (price, size, time)
            - Latest quote (bid/ask)
            - Today's OHLCV data
            - Previous day's close
            - Updated timestamp

        Example Usage:
            - get_stock_snapshot("AAPL")
            - get_stock_snapshot("NVDA")
            - get_stock_snapshot("TSLA")

        Related Tools:
            - get_snapshot_ticker: The underlying API this uses
            - get_latest_stock_price: Just the price
            - get_simple_quote: Just the quote
        """
        try:
            return await get_snapshot_ticker(market_type="stocks", ticker=ticker)
        except Exception as e:
            return build_error_response(e, f"Getting snapshot for {ticker}")
