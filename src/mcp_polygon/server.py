import os
import json
from typing import Optional, Any, Dict, Union, List, Literal
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from polygon import RESTClient
from importlib.metadata import version, PackageNotFoundError

from datetime import datetime, date, timedelta

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")
if not POLYGON_API_KEY:
    print("Warning: POLYGON_API_KEY environment variable not set.")

version_number = "MCP-Polygon/unknown"
try:
    version_number = f"MCP-Polygon/{version('mcp_polygon')}"
except PackageNotFoundError:
    pass

polygon_client = RESTClient(POLYGON_API_KEY)
polygon_client.headers["User-Agent"] += f" {version_number}"

poly_mcp = FastMCP("Polygon", dependencies=["polygon"])


# ========================================
# Helper Functions for Better LLM Experience
# ========================================


def _validate_ticker(ticker: str) -> bool:
    """
    Validate ticker format.

    Args:
        ticker: Ticker symbol to validate

    Returns:
        True if valid format
    """
    if not ticker or not isinstance(ticker, str):
        return False
    # Basic validation - alphanumeric and some special chars
    return len(ticker) >= 1 and len(ticker) <= 20


def _format_date_for_api(date_input: Union[str, datetime, date]) -> str:
    """
    Convert various date formats to API-friendly YYYY-MM-DD string.

    Args:
        date_input: Date as string, datetime, or date object

    Returns:
        Date string in YYYY-MM-DD format
    """
    if isinstance(date_input, str):
        return date_input
    elif isinstance(date_input, datetime):
        return date_input.strftime("%Y-%m-%d")
    elif isinstance(date_input, date):
        return date_input.strftime("%Y-%m-%d")
    return str(date_input)


def _get_date_range_default(days_back: int = 30) -> tuple[str, str]:
    """
    Get default date range for queries (today minus N days to today).

    Args:
        days_back: Number of days to go back from today

    Returns:
        Tuple of (from_date, to_date) as YYYY-MM-DD strings
    """
    today = date.today()
    from_date = today - timedelta(days=days_back)
    return from_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def _build_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """
    Build a helpful error response with context for LLMs.

    Args:
        error: The exception that occurred
        context: Additional context about what was being attempted

    Returns:
        Error response dictionary with helpful message
    """
    error_msg = str(error)
    response = {"error": error_msg, "status": "failed"}

    if context:
        response["context"] = context

    # Add helpful hints based on error type
    if "401" in error_msg or "Unauthorized" in error_msg:
        response["hint"] = (
            "API key may be invalid or missing. Check POLYGON_API_KEY environment variable."
        )
    elif "404" in error_msg or "Not Found" in error_msg:
        response["hint"] = "Resource not found. Check ticker symbol or date is valid."
    elif "429" in error_msg or "rate limit" in error_msg.lower():
        response["hint"] = "API rate limit exceeded. Wait a moment before retrying."
    elif "400" in error_msg or "Bad Request" in error_msg:
        response["hint"] = (
            "Invalid request parameters. Check date formats (YYYY-MM-DD) and parameter values."
        )

    return response


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting aggregates for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Listing aggregates for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting daily OHLC for {ticker} on {date}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting previous close for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Listing trades for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting last trade for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_last_crypto_trade(
    from_: str,
    to: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get the most recent trade for a crypto pair.
    """
    try:
        results = polygon_client.get_last_crypto_trade(
            from_=from_, to=to, params=params, raw=True
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Listing quotes for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting last quote for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_last_forex_quote(
    from_: str,
    to: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get the most recent forex quote.
    """
    try:
        results = polygon_client.get_last_forex_quote(
            from_=from_, to=to, params=params, raw=True
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_real_time_currency_conversion(
    from_: str,
    to: str,
    amount: Optional[float] = None,
    precision: Optional[int] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get real-time currency conversion.
    """
    try:
        results = polygon_client.get_real_time_currency_conversion(
            from_=from_,
            to=to,
            amount=amount,
            precision=precision,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(
            e, f"Getting snapshot for {ticker} in {market_type} market"
        )


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_snapshot_option(
    underlying_asset: str,
    option_contract: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get snapshot for a specific option contract.
    """
    try:
        results = polygon_client.get_snapshot_option(
            underlying_asset=underlying_asset,
            option_contract=option_contract,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_snapshot_crypto_book(
    ticker: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get snapshot for a crypto ticker's order book.
    """
    try:
        results = polygon_client.get_snapshot_crypto_book(
            ticker=ticker, params=params, raw=True
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_market_holidays(
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get upcoming market holidays and their open/close times.
    """
    try:
        results = polygon_client.get_market_holidays(params=params, raw=True)

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_market_status(
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get the current trading status of the stock market and exchanges.

    This tells you whether the market is currently open, closed, or in pre/post-market
    trading. Also provides status for different exchanges and market types. Essential
    for knowing if you can expect real-time data or if the market is closed.

    Args:
        params: Additional query parameters as a dictionary

    Returns:
        JSON response containing market status information:
        - market: Overall market status - "open", "closed", or "extended-hours"
        - serverTime: Current server time (ISO 8601 format)
        - exchanges: Object containing individual exchange statuses:
            - nyse: New York Stock Exchange status
            - nasdaq: NASDAQ status
            - otc: Over-the-counter market status
        - currencies: Forex market status
            - fx: Foreign exchange market status
            - crypto: Cryptocurrency market status
        - earlyHours: Whether pre-market trading is active
        - afterHours: Whether after-hours trading is active

    Example Usage:
        - Check if market is open: get_market_status()
        - Verify trading hours: get_market_status()
        - Check exchange status: get_market_status()

    Related Tools:
        - get_market_holidays: Get upcoming market holidays and closures
        - get_snapshot_ticker: Get real-time ticker data (available during market hours)
        - get_last_trade: Get most recent trade (may be delayed if market closed)
    """
    try:
        results = polygon_client.get_market_status(params=params, raw=True)

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return _build_error_response(e, "Getting market status")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, "Listing tickers")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting details for ticker {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(
            e, f"Listing news for {ticker if ticker else 'market'}"
        )


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(
            e, f"Listing splits{' for ' + ticker if ticker else ''}"
        )


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(
            e, f"Listing dividends{' for ' + ticker if ticker else ''}"
        )


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_analyst_insights(
    date: Optional[Union[str, date]] = None,
    date_any_of: Optional[str] = None,
    date_gt: Optional[Union[str, date]] = None,
    date_gte: Optional[Union[str, date]] = None,
    date_lt: Optional[Union[str, date]] = None,
    date_lte: Optional[Union[str, date]] = None,
    ticker: Optional[str] = None,
    ticker_any_of: Optional[str] = None,
    ticker_gt: Optional[str] = None,
    ticker_gte: Optional[str] = None,
    ticker_lt: Optional[str] = None,
    ticker_lte: Optional[str] = None,
    last_updated: Optional[str] = None,
    last_updated_any_of: Optional[str] = None,
    last_updated_gt: Optional[str] = None,
    last_updated_gte: Optional[str] = None,
    last_updated_lt: Optional[str] = None,
    last_updated_lte: Optional[str] = None,
    firm: Optional[str] = None,
    firm_any_of: Optional[str] = None,
    firm_gt: Optional[str] = None,
    firm_gte: Optional[str] = None,
    firm_lt: Optional[str] = None,
    firm_lte: Optional[str] = None,
    rating_action: Optional[str] = None,
    rating_action_any_of: Optional[str] = None,
    rating_action_gt: Optional[str] = None,
    rating_action_gte: Optional[str] = None,
    rating_action_lt: Optional[str] = None,
    rating_action_lte: Optional[str] = None,
    benzinga_firm_id: Optional[str] = None,
    benzinga_firm_id_any_of: Optional[str] = None,
    benzinga_firm_id_gt: Optional[str] = None,
    benzinga_firm_id_gte: Optional[str] = None,
    benzinga_firm_id_lt: Optional[str] = None,
    benzinga_firm_id_lte: Optional[str] = None,
    benzinga_rating_id: Optional[str] = None,
    benzinga_rating_id_any_of: Optional[str] = None,
    benzinga_rating_id_gt: Optional[str] = None,
    benzinga_rating_id_gte: Optional[str] = None,
    benzinga_rating_id_lt: Optional[str] = None,
    benzinga_rating_id_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga analyst insights.
    """
    try:
        results = polygon_client.list_benzinga_analyst_insights(
            date=date,
            date_any_of=date_any_of,
            date_gt=date_gt,
            date_gte=date_gte,
            date_lt=date_lt,
            date_lte=date_lte,
            ticker=ticker,
            ticker_any_of=ticker_any_of,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            last_updated=last_updated,
            last_updated_any_of=last_updated_any_of,
            last_updated_gt=last_updated_gt,
            last_updated_gte=last_updated_gte,
            last_updated_lt=last_updated_lt,
            last_updated_lte=last_updated_lte,
            firm=firm,
            firm_any_of=firm_any_of,
            firm_gt=firm_gt,
            firm_gte=firm_gte,
            firm_lt=firm_lt,
            firm_lte=firm_lte,
            rating_action=rating_action,
            rating_action_any_of=rating_action_any_of,
            rating_action_gt=rating_action_gt,
            rating_action_gte=rating_action_gte,
            rating_action_lt=rating_action_lt,
            rating_action_lte=rating_action_lte,
            benzinga_firm_id=benzinga_firm_id,
            benzinga_firm_id_any_of=benzinga_firm_id_any_of,
            benzinga_firm_id_gt=benzinga_firm_id_gt,
            benzinga_firm_id_gte=benzinga_firm_id_gte,
            benzinga_firm_id_lt=benzinga_firm_id_lt,
            benzinga_firm_id_lte=benzinga_firm_id_lte,
            benzinga_rating_id=benzinga_rating_id,
            benzinga_rating_id_any_of=benzinga_rating_id_any_of,
            benzinga_rating_id_gt=benzinga_rating_id_gt,
            benzinga_rating_id_gte=benzinga_rating_id_gte,
            benzinga_rating_id_lt=benzinga_rating_id_lt,
            benzinga_rating_id_lte=benzinga_rating_id_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_analysts(
    benzinga_id: Optional[str] = None,
    benzinga_id_any_of: Optional[str] = None,
    benzinga_id_gt: Optional[str] = None,
    benzinga_id_gte: Optional[str] = None,
    benzinga_id_lt: Optional[str] = None,
    benzinga_id_lte: Optional[str] = None,
    benzinga_firm_id: Optional[str] = None,
    benzinga_firm_id_any_of: Optional[str] = None,
    benzinga_firm_id_gt: Optional[str] = None,
    benzinga_firm_id_gte: Optional[str] = None,
    benzinga_firm_id_lt: Optional[str] = None,
    benzinga_firm_id_lte: Optional[str] = None,
    firm_name: Optional[str] = None,
    firm_name_any_of: Optional[str] = None,
    firm_name_gt: Optional[str] = None,
    firm_name_gte: Optional[str] = None,
    firm_name_lt: Optional[str] = None,
    firm_name_lte: Optional[str] = None,
    full_name: Optional[str] = None,
    full_name_any_of: Optional[str] = None,
    full_name_gt: Optional[str] = None,
    full_name_gte: Optional[str] = None,
    full_name_lt: Optional[str] = None,
    full_name_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga analysts.
    """
    try:
        results = polygon_client.list_benzinga_analysts(
            benzinga_id=benzinga_id,
            benzinga_id_any_of=benzinga_id_any_of,
            benzinga_id_gt=benzinga_id_gt,
            benzinga_id_gte=benzinga_id_gte,
            benzinga_id_lt=benzinga_id_lt,
            benzinga_id_lte=benzinga_id_lte,
            benzinga_firm_id=benzinga_firm_id,
            benzinga_firm_id_any_of=benzinga_firm_id_any_of,
            benzinga_firm_id_gt=benzinga_firm_id_gt,
            benzinga_firm_id_gte=benzinga_firm_id_gte,
            benzinga_firm_id_lt=benzinga_firm_id_lt,
            benzinga_firm_id_lte=benzinga_firm_id_lte,
            firm_name=firm_name,
            firm_name_any_of=firm_name_any_of,
            firm_name_gt=firm_name_gt,
            firm_name_gte=firm_name_gte,
            firm_name_lt=firm_name_lt,
            firm_name_lte=firm_name_lte,
            full_name=full_name,
            full_name_any_of=full_name_any_of,
            full_name_gt=full_name_gt,
            full_name_gte=full_name_gte,
            full_name_lt=full_name_lt,
            full_name_lte=full_name_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_consensus_ratings(
    ticker: str,
    date: Optional[Union[str, date]] = None,
    date_gt: Optional[Union[str, date]] = None,
    date_gte: Optional[Union[str, date]] = None,
    date_lt: Optional[Union[str, date]] = None,
    date_lte: Optional[Union[str, date]] = None,
    limit: Optional[int] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga consensus ratings for a ticker.
    """
    try:
        results = polygon_client.list_benzinga_consensus_ratings(
            ticker=ticker,
            date=date,
            date_gt=date_gt,
            date_gte=date_gte,
            date_lt=date_lt,
            date_lte=date_lte,
            limit=limit,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_earnings(
    date: Optional[Union[str, date]] = None,
    date_any_of: Optional[str] = None,
    date_gt: Optional[Union[str, date]] = None,
    date_gte: Optional[Union[str, date]] = None,
    date_lt: Optional[Union[str, date]] = None,
    date_lte: Optional[Union[str, date]] = None,
    ticker: Optional[str] = None,
    ticker_any_of: Optional[str] = None,
    ticker_gt: Optional[str] = None,
    ticker_gte: Optional[str] = None,
    ticker_lt: Optional[str] = None,
    ticker_lte: Optional[str] = None,
    importance: Optional[int] = None,
    importance_any_of: Optional[str] = None,
    importance_gt: Optional[int] = None,
    importance_gte: Optional[int] = None,
    importance_lt: Optional[int] = None,
    importance_lte: Optional[int] = None,
    last_updated: Optional[str] = None,
    last_updated_any_of: Optional[str] = None,
    last_updated_gt: Optional[str] = None,
    last_updated_gte: Optional[str] = None,
    last_updated_lt: Optional[str] = None,
    last_updated_lte: Optional[str] = None,
    date_status: Optional[str] = None,
    date_status_any_of: Optional[str] = None,
    date_status_gt: Optional[str] = None,
    date_status_gte: Optional[str] = None,
    date_status_lt: Optional[str] = None,
    date_status_lte: Optional[str] = None,
    eps_surprise_percent: Optional[float] = None,
    eps_surprise_percent_any_of: Optional[str] = None,
    eps_surprise_percent_gt: Optional[float] = None,
    eps_surprise_percent_gte: Optional[float] = None,
    eps_surprise_percent_lt: Optional[float] = None,
    eps_surprise_percent_lte: Optional[float] = None,
    revenue_surprise_percent: Optional[float] = None,
    revenue_surprise_percent_any_of: Optional[str] = None,
    revenue_surprise_percent_gt: Optional[float] = None,
    revenue_surprise_percent_gte: Optional[float] = None,
    revenue_surprise_percent_lt: Optional[float] = None,
    revenue_surprise_percent_lte: Optional[float] = None,
    fiscal_year: Optional[int] = None,
    fiscal_year_any_of: Optional[str] = None,
    fiscal_year_gt: Optional[int] = None,
    fiscal_year_gte: Optional[int] = None,
    fiscal_year_lt: Optional[int] = None,
    fiscal_year_lte: Optional[int] = None,
    fiscal_period: Optional[str] = None,
    fiscal_period_any_of: Optional[str] = None,
    fiscal_period_gt: Optional[str] = None,
    fiscal_period_gte: Optional[str] = None,
    fiscal_period_lt: Optional[str] = None,
    fiscal_period_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga earnings.
    """
    try:
        results = polygon_client.list_benzinga_earnings(
            date=date,
            date_any_of=date_any_of,
            date_gt=date_gt,
            date_gte=date_gte,
            date_lt=date_lt,
            date_lte=date_lte,
            ticker=ticker,
            ticker_any_of=ticker_any_of,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            importance=importance,
            importance_any_of=importance_any_of,
            importance_gt=importance_gt,
            importance_gte=importance_gte,
            importance_lt=importance_lt,
            importance_lte=importance_lte,
            last_updated=last_updated,
            last_updated_any_of=last_updated_any_of,
            last_updated_gt=last_updated_gt,
            last_updated_gte=last_updated_gte,
            last_updated_lt=last_updated_lt,
            last_updated_lte=last_updated_lte,
            date_status=date_status,
            date_status_any_of=date_status_any_of,
            date_status_gt=date_status_gt,
            date_status_gte=date_status_gte,
            date_status_lt=date_status_lt,
            date_status_lte=date_status_lte,
            eps_surprise_percent=eps_surprise_percent,
            eps_surprise_percent_any_of=eps_surprise_percent_any_of,
            eps_surprise_percent_gt=eps_surprise_percent_gt,
            eps_surprise_percent_gte=eps_surprise_percent_gte,
            eps_surprise_percent_lt=eps_surprise_percent_lt,
            eps_surprise_percent_lte=eps_surprise_percent_lte,
            revenue_surprise_percent=revenue_surprise_percent,
            revenue_surprise_percent_any_of=revenue_surprise_percent_any_of,
            revenue_surprise_percent_gt=revenue_surprise_percent_gt,
            revenue_surprise_percent_gte=revenue_surprise_percent_gte,
            revenue_surprise_percent_lt=revenue_surprise_percent_lt,
            revenue_surprise_percent_lte=revenue_surprise_percent_lte,
            fiscal_year=fiscal_year,
            fiscal_year_any_of=fiscal_year_any_of,
            fiscal_year_gt=fiscal_year_gt,
            fiscal_year_gte=fiscal_year_gte,
            fiscal_year_lt=fiscal_year_lt,
            fiscal_year_lte=fiscal_year_lte,
            fiscal_period=fiscal_period,
            fiscal_period_any_of=fiscal_period_any_of,
            fiscal_period_gt=fiscal_period_gt,
            fiscal_period_gte=fiscal_period_gte,
            fiscal_period_lt=fiscal_period_lt,
            fiscal_period_lte=fiscal_period_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_firms(
    benzinga_id: Optional[str] = None,
    benzinga_id_any_of: Optional[str] = None,
    benzinga_id_gt: Optional[str] = None,
    benzinga_id_gte: Optional[str] = None,
    benzinga_id_lt: Optional[str] = None,
    benzinga_id_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga firms.
    """
    try:
        results = polygon_client.list_benzinga_firms(
            benzinga_id=benzinga_id,
            benzinga_id_any_of=benzinga_id_any_of,
            benzinga_id_gt=benzinga_id_gt,
            benzinga_id_gte=benzinga_id_gte,
            benzinga_id_lt=benzinga_id_lt,
            benzinga_id_lte=benzinga_id_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_guidance(
    date: Optional[Union[str, date]] = None,
    date_any_of: Optional[str] = None,
    date_gt: Optional[Union[str, date]] = None,
    date_gte: Optional[Union[str, date]] = None,
    date_lt: Optional[Union[str, date]] = None,
    date_lte: Optional[Union[str, date]] = None,
    ticker: Optional[str] = None,
    ticker_any_of: Optional[str] = None,
    ticker_gt: Optional[str] = None,
    ticker_gte: Optional[str] = None,
    ticker_lt: Optional[str] = None,
    ticker_lte: Optional[str] = None,
    positioning: Optional[str] = None,
    positioning_any_of: Optional[str] = None,
    positioning_gt: Optional[str] = None,
    positioning_gte: Optional[str] = None,
    positioning_lt: Optional[str] = None,
    positioning_lte: Optional[str] = None,
    importance: Optional[int] = None,
    importance_any_of: Optional[str] = None,
    importance_gt: Optional[int] = None,
    importance_gte: Optional[int] = None,
    importance_lt: Optional[int] = None,
    importance_lte: Optional[int] = None,
    last_updated: Optional[str] = None,
    last_updated_any_of: Optional[str] = None,
    last_updated_gt: Optional[str] = None,
    last_updated_gte: Optional[str] = None,
    last_updated_lt: Optional[str] = None,
    last_updated_lte: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_year_any_of: Optional[str] = None,
    fiscal_year_gt: Optional[int] = None,
    fiscal_year_gte: Optional[int] = None,
    fiscal_year_lt: Optional[int] = None,
    fiscal_year_lte: Optional[int] = None,
    fiscal_period: Optional[str] = None,
    fiscal_period_any_of: Optional[str] = None,
    fiscal_period_gt: Optional[str] = None,
    fiscal_period_gte: Optional[str] = None,
    fiscal_period_lt: Optional[str] = None,
    fiscal_period_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga guidance.
    """
    try:
        results = polygon_client.list_benzinga_guidance(
            date=date,
            date_any_of=date_any_of,
            date_gt=date_gt,
            date_gte=date_gte,
            date_lt=date_lt,
            date_lte=date_lte,
            ticker=ticker,
            ticker_any_of=ticker_any_of,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            positioning=positioning,
            positioning_any_of=positioning_any_of,
            positioning_gt=positioning_gt,
            positioning_gte=positioning_gte,
            positioning_lt=positioning_lt,
            positioning_lte=positioning_lte,
            importance=importance,
            importance_any_of=importance_any_of,
            importance_gt=importance_gt,
            importance_gte=importance_gte,
            importance_lt=importance_lt,
            importance_lte=importance_lte,
            last_updated=last_updated,
            last_updated_any_of=last_updated_any_of,
            last_updated_gt=last_updated_gt,
            last_updated_gte=last_updated_gte,
            last_updated_lt=last_updated_lt,
            last_updated_lte=last_updated_lte,
            fiscal_year=fiscal_year,
            fiscal_year_any_of=fiscal_year_any_of,
            fiscal_year_gt=fiscal_year_gt,
            fiscal_year_gte=fiscal_year_gte,
            fiscal_year_lt=fiscal_year_lt,
            fiscal_year_lte=fiscal_year_lte,
            fiscal_period=fiscal_period,
            fiscal_period_any_of=fiscal_period_any_of,
            fiscal_period_gt=fiscal_period_gt,
            fiscal_period_gte=fiscal_period_gte,
            fiscal_period_lt=fiscal_period_lt,
            fiscal_period_lte=fiscal_period_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_news(
    published: Optional[str] = None,
    published_any_of: Optional[str] = None,
    published_gt: Optional[str] = None,
    published_gte: Optional[str] = None,
    published_lt: Optional[str] = None,
    published_lte: Optional[str] = None,
    last_updated: Optional[str] = None,
    last_updated_any_of: Optional[str] = None,
    last_updated_gt: Optional[str] = None,
    last_updated_gte: Optional[str] = None,
    last_updated_lt: Optional[str] = None,
    last_updated_lte: Optional[str] = None,
    tickers: Optional[str] = None,
    tickers_all_of: Optional[str] = None,
    tickers_any_of: Optional[str] = None,
    channels: Optional[str] = None,
    channels_all_of: Optional[str] = None,
    channels_any_of: Optional[str] = None,
    tags: Optional[str] = None,
    tags_all_of: Optional[str] = None,
    tags_any_of: Optional[str] = None,
    author: Optional[str] = None,
    author_any_of: Optional[str] = None,
    author_gt: Optional[str] = None,
    author_gte: Optional[str] = None,
    author_lt: Optional[str] = None,
    author_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga news.
    """
    try:
        results = polygon_client.list_benzinga_news(
            published=published,
            published_any_of=published_any_of,
            published_gt=published_gt,
            published_gte=published_gte,
            published_lt=published_lt,
            published_lte=published_lte,
            last_updated=last_updated,
            last_updated_any_of=last_updated_any_of,
            last_updated_gt=last_updated_gt,
            last_updated_gte=last_updated_gte,
            last_updated_lt=last_updated_lt,
            last_updated_lte=last_updated_lte,
            tickers=tickers,
            tickers_all_of=tickers_all_of,
            tickers_any_of=tickers_any_of,
            channels=channels,
            channels_all_of=channels_all_of,
            channels_any_of=channels_any_of,
            tags=tags,
            tags_all_of=tags_all_of,
            tags_any_of=tags_any_of,
            author=author,
            author_any_of=author_any_of,
            author_gt=author_gt,
            author_gte=author_gte,
            author_lt=author_lt,
            author_lte=author_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_benzinga_ratings(
    date: Optional[Union[str, date]] = None,
    date_any_of: Optional[str] = None,
    date_gt: Optional[Union[str, date]] = None,
    date_gte: Optional[Union[str, date]] = None,
    date_lt: Optional[Union[str, date]] = None,
    date_lte: Optional[Union[str, date]] = None,
    ticker: Optional[str] = None,
    ticker_any_of: Optional[str] = None,
    ticker_gt: Optional[str] = None,
    ticker_gte: Optional[str] = None,
    ticker_lt: Optional[str] = None,
    ticker_lte: Optional[str] = None,
    importance: Optional[int] = None,
    importance_any_of: Optional[str] = None,
    importance_gt: Optional[int] = None,
    importance_gte: Optional[int] = None,
    importance_lt: Optional[int] = None,
    importance_lte: Optional[int] = None,
    last_updated: Optional[str] = None,
    last_updated_any_of: Optional[str] = None,
    last_updated_gt: Optional[str] = None,
    last_updated_gte: Optional[str] = None,
    last_updated_lt: Optional[str] = None,
    last_updated_lte: Optional[str] = None,
    rating_action: Optional[str] = None,
    rating_action_any_of: Optional[str] = None,
    rating_action_gt: Optional[str] = None,
    rating_action_gte: Optional[str] = None,
    rating_action_lt: Optional[str] = None,
    rating_action_lte: Optional[str] = None,
    price_target_action: Optional[str] = None,
    price_target_action_any_of: Optional[str] = None,
    price_target_action_gt: Optional[str] = None,
    price_target_action_gte: Optional[str] = None,
    price_target_action_lt: Optional[str] = None,
    price_target_action_lte: Optional[str] = None,
    benzinga_id: Optional[str] = None,
    benzinga_id_any_of: Optional[str] = None,
    benzinga_id_gt: Optional[str] = None,
    benzinga_id_gte: Optional[str] = None,
    benzinga_id_lt: Optional[str] = None,
    benzinga_id_lte: Optional[str] = None,
    benzinga_analyst_id: Optional[str] = None,
    benzinga_analyst_id_any_of: Optional[str] = None,
    benzinga_analyst_id_gt: Optional[str] = None,
    benzinga_analyst_id_gte: Optional[str] = None,
    benzinga_analyst_id_lt: Optional[str] = None,
    benzinga_analyst_id_lte: Optional[str] = None,
    benzinga_firm_id: Optional[str] = None,
    benzinga_firm_id_any_of: Optional[str] = None,
    benzinga_firm_id_gt: Optional[str] = None,
    benzinga_firm_id_gte: Optional[str] = None,
    benzinga_firm_id_lt: Optional[str] = None,
    benzinga_firm_id_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List Benzinga ratings.
    """
    try:
        results = polygon_client.list_benzinga_ratings(
            date=date,
            date_any_of=date_any_of,
            date_gt=date_gt,
            date_gte=date_gte,
            date_lt=date_lt,
            date_lte=date_lte,
            ticker=ticker,
            ticker_any_of=ticker_any_of,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            importance=importance,
            importance_any_of=importance_any_of,
            importance_gt=importance_gt,
            importance_gte=importance_gte,
            importance_lt=importance_lt,
            importance_lte=importance_lte,
            last_updated=last_updated,
            last_updated_any_of=last_updated_any_of,
            last_updated_gt=last_updated_gt,
            last_updated_gte=last_updated_gte,
            last_updated_lt=last_updated_lt,
            last_updated_lte=last_updated_lte,
            rating_action=rating_action,
            rating_action_any_of=rating_action_any_of,
            rating_action_gt=rating_action_gt,
            rating_action_gte=rating_action_gte,
            rating_action_lt=rating_action_lt,
            rating_action_lte=rating_action_lte,
            price_target_action=price_target_action,
            price_target_action_any_of=price_target_action_any_of,
            price_target_action_gt=price_target_action_gt,
            price_target_action_gte=price_target_action_gte,
            price_target_action_lt=price_target_action_lt,
            price_target_action_lte=price_target_action_lte,
            benzinga_id=benzinga_id,
            benzinga_id_any_of=benzinga_id_any_of,
            benzinga_id_gt=benzinga_id_gt,
            benzinga_id_gte=benzinga_id_gte,
            benzinga_id_lt=benzinga_id_lt,
            benzinga_id_lte=benzinga_id_lte,
            benzinga_analyst_id=benzinga_analyst_id,
            benzinga_analyst_id_any_of=benzinga_analyst_id_any_of,
            benzinga_analyst_id_gt=benzinga_analyst_id_gt,
            benzinga_analyst_id_gte=benzinga_analyst_id_gte,
            benzinga_analyst_id_lt=benzinga_analyst_id_lt,
            benzinga_analyst_id_lte=benzinga_analyst_id_lte,
            benzinga_firm_id=benzinga_firm_id,
            benzinga_firm_id_any_of=benzinga_firm_id_any_of,
            benzinga_firm_id_gt=benzinga_firm_id_gt,
            benzinga_firm_id_gte=benzinga_firm_id_gte,
            benzinga_firm_id_lt=benzinga_firm_id_lt,
            benzinga_firm_id_lte=benzinga_firm_id_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_aggregates(
    ticker: str,
    resolution: str,
    window_start: Optional[str] = None,
    window_start_lt: Optional[str] = None,
    window_start_lte: Optional[str] = None,
    window_start_gt: Optional[str] = None,
    window_start_gte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get aggregates for a futures contract in a given time range.
    """
    try:
        results = polygon_client.list_futures_aggregates(
            ticker=ticker,
            resolution=resolution,
            window_start=window_start,
            window_start_lt=window_start_lt,
            window_start_lte=window_start_lte,
            window_start_gt=window_start_gt,
            window_start_gte=window_start_gte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_contracts(
    product_code: Optional[str] = None,
    first_trade_date: Optional[Union[str, date]] = None,
    last_trade_date: Optional[Union[str, date]] = None,
    as_of: Optional[Union[str, date]] = None,
    active: Optional[str] = None,
    type: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get a paginated list of futures contracts.
    """
    try:
        results = polygon_client.list_futures_contracts(
            product_code=product_code,
            first_trade_date=first_trade_date,
            last_trade_date=last_trade_date,
            as_of=as_of,
            active=active,
            type=type,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_futures_contract_details(
    ticker: str,
    as_of: Optional[Union[str, date]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get details for a single futures contract at a specified point in time.
    """
    try:
        results = polygon_client.get_futures_contract_details(
            ticker=ticker,
            as_of=as_of,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_products(
    name: Optional[str] = None,
    name_search: Optional[str] = None,
    as_of: Optional[Union[str, date]] = None,
    trading_venue: Optional[str] = None,
    sector: Optional[str] = None,
    sub_sector: Optional[str] = None,
    asset_class: Optional[str] = None,
    asset_sub_class: Optional[str] = None,
    type: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get a list of futures products (including combos).
    """
    try:
        results = polygon_client.list_futures_products(
            name=name,
            name_search=name_search,
            as_of=as_of,
            trading_venue=trading_venue,
            sector=sector,
            sub_sector=sub_sector,
            asset_class=asset_class,
            asset_sub_class=asset_sub_class,
            type=type,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_futures_product_details(
    product_code: str,
    type: Optional[str] = None,
    as_of: Optional[Union[str, date]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get details for a single futures product as it was at a specific day.
    """
    try:
        results = polygon_client.get_futures_product_details(
            product_code=product_code,
            type=type,
            as_of=as_of,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_quotes(
    ticker: str,
    timestamp: Optional[str] = None,
    timestamp_lt: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    timestamp_gt: Optional[str] = None,
    timestamp_gte: Optional[str] = None,
    session_end_date: Optional[str] = None,
    session_end_date_lt: Optional[str] = None,
    session_end_date_lte: Optional[str] = None,
    session_end_date_gt: Optional[str] = None,
    session_end_date_gte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get quotes for a futures contract in a given time range.
    """
    try:
        results = polygon_client.list_futures_quotes(
            ticker=ticker,
            timestamp=timestamp,
            timestamp_lt=timestamp_lt,
            timestamp_lte=timestamp_lte,
            timestamp_gt=timestamp_gt,
            timestamp_gte=timestamp_gte,
            session_end_date=session_end_date,
            session_end_date_lt=session_end_date_lt,
            session_end_date_lte=session_end_date_lte,
            session_end_date_gt=session_end_date_gt,
            session_end_date_gte=session_end_date_gte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_trades(
    ticker: str,
    timestamp: Optional[str] = None,
    timestamp_lt: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    timestamp_gt: Optional[str] = None,
    timestamp_gte: Optional[str] = None,
    session_end_date: Optional[str] = None,
    session_end_date_lt: Optional[str] = None,
    session_end_date_lte: Optional[str] = None,
    session_end_date_gt: Optional[str] = None,
    session_end_date_gte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get trades for a futures contract in a given time range.
    """
    try:
        results = polygon_client.list_futures_trades(
            ticker=ticker,
            timestamp=timestamp,
            timestamp_lt=timestamp_lt,
            timestamp_lte=timestamp_lte,
            timestamp_gt=timestamp_gt,
            timestamp_gte=timestamp_gte,
            session_end_date=session_end_date,
            session_end_date_lt=session_end_date_lt,
            session_end_date_lte=session_end_date_lte,
            session_end_date_gt=session_end_date_gt,
            session_end_date_gte=session_end_date_gte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_schedules(
    session_end_date: Optional[str] = None,
    trading_venue: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get trading schedules for multiple futures products on a specific date.
    """
    try:
        results = polygon_client.list_futures_schedules(
            session_end_date=session_end_date,
            trading_venue=trading_venue,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_schedules_by_product_code(
    product_code: str,
    session_end_date: Optional[str] = None,
    session_end_date_lt: Optional[str] = None,
    session_end_date_lte: Optional[str] = None,
    session_end_date_gt: Optional[str] = None,
    session_end_date_gte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get schedule data for a single futures product across many trading dates.
    """
    try:
        results = polygon_client.list_futures_schedules_by_product_code(
            product_code=product_code,
            session_end_date=session_end_date,
            session_end_date_lt=session_end_date_lt,
            session_end_date_lte=session_end_date_lte,
            session_end_date_gt=session_end_date_gt,
            session_end_date_gte=session_end_date_gte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_futures_market_statuses(
    product_code_any_of: Optional[str] = None,
    product_code: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get market statuses for futures products.
    """
    try:
        results = polygon_client.list_futures_market_statuses(
            product_code_any_of=product_code_any_of,
            product_code=product_code,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_sma(
    ticker: str,
    timestamp: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lte: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gte: Optional[Union[str, int, datetime, date]] = None,
    timespan: Optional[str] = None,
    window: Optional[int] = None,
    adjusted: Optional[bool] = None,
    expand_underlying: Optional[bool] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    series_type: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get Simple Moving Average (SMA) values for a ticker over a given time range.
    """
    try:
        results = polygon_client.get_sma(
            ticker=ticker,
            timestamp=timestamp,
            timestamp_lt=timestamp_lt,
            timestamp_lte=timestamp_lte,
            timestamp_gt=timestamp_gt,
            timestamp_gte=timestamp_gte,
            timespan=timespan,
            window=window,
            adjusted=adjusted,
            expand_underlying=expand_underlying,
            order=order,
            limit=limit,
            series_type=series_type,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_ema(
    ticker: str,
    timestamp: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lte: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gte: Optional[Union[str, int, datetime, date]] = None,
    timespan: Optional[str] = None,
    window: Optional[int] = None,
    adjusted: Optional[bool] = None,
    expand_underlying: Optional[bool] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    series_type: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get Exponential Moving Average (EMA) values for a ticker over a given time range.
    """
    try:
        results = polygon_client.get_ema(
            ticker=ticker,
            timestamp=timestamp,
            timestamp_lt=timestamp_lt,
            timestamp_lte=timestamp_lte,
            timestamp_gt=timestamp_gt,
            timestamp_gte=timestamp_gte,
            timespan=timespan,
            window=window,
            adjusted=adjusted,
            expand_underlying=expand_underlying,
            order=order,
            limit=limit,
            series_type=series_type,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_rsi(
    ticker: str,
    timestamp: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lte: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gte: Optional[Union[str, int, datetime, date]] = None,
    timespan: Optional[str] = None,
    window: Optional[int] = None,
    adjusted: Optional[bool] = None,
    expand_underlying: Optional[bool] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    series_type: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get Relative Strength Index (RSI) values for a ticker over a given time range.
    """
    try:
        results = polygon_client.get_rsi(
            ticker=ticker,
            timestamp=timestamp,
            timestamp_lt=timestamp_lt,
            timestamp_lte=timestamp_lte,
            timestamp_gt=timestamp_gt,
            timestamp_gte=timestamp_gte,
            timespan=timespan,
            window=window,
            adjusted=adjusted,
            expand_underlying=expand_underlying,
            order=order,
            limit=limit,
            series_type=series_type,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_macd(
    ticker: str,
    timestamp: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_lte: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gt: Optional[Union[str, int, datetime, date]] = None,
    timestamp_gte: Optional[Union[str, int, datetime, date]] = None,
    timespan: Optional[str] = None,
    short_window: Optional[int] = None,
    long_window: Optional[int] = None,
    signal_window: Optional[int] = None,
    adjusted: Optional[bool] = None,
    expand_underlying: Optional[bool] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    series_type: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get MACD (Moving Average Convergence Divergence) values for a ticker over a given time range.
    """
    try:
        results = polygon_client.get_macd(
            ticker=ticker,
            timestamp=timestamp,
            timestamp_lt=timestamp_lt,
            timestamp_lte=timestamp_lte,
            timestamp_gt=timestamp_gt,
            timestamp_gte=timestamp_gte,
            timespan=timespan,
            short_window=short_window,
            long_window=long_window,
            signal_window=signal_window,
            adjusted=adjusted,
            expand_underlying=expand_underlying,
            order=order,
            limit=limit,
            series_type=series_type,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_futures_snapshot(
    ticker: Optional[str] = None,
    ticker_any_of: Optional[str] = None,
    ticker_gt: Optional[str] = None,
    ticker_gte: Optional[str] = None,
    ticker_lt: Optional[str] = None,
    ticker_lte: Optional[str] = None,
    product_code: Optional[str] = None,
    product_code_any_of: Optional[str] = None,
    product_code_gt: Optional[str] = None,
    product_code_gte: Optional[str] = None,
    product_code_lt: Optional[str] = None,
    product_code_lte: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get snapshots for futures contracts.
    """
    try:
        results = polygon_client.get_futures_snapshot(
            ticker=ticker,
            ticker_any_of=ticker_any_of,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            product_code=product_code,
            product_code_any_of=product_code_any_of,
            product_code_gt=product_code_gt,
            product_code_gte=product_code_gte,
            product_code_lt=product_code_lt,
            product_code_lte=product_code_lte,
            limit=limit,
            sort=sort,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_options_contract(
    ticker: str,
    as_of: Optional[Union[str, date]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get details for a specific options contract.
    """
    try:
        results = polygon_client.get_options_contract(
            ticker=ticker,
            as_of=as_of,
            params=params,
            raw=True,
        )

        data_str = results.data.decode("utf-8")
        return json.loads(data_str)
    except Exception as e:
        return {"error": str(e)}


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_options_contracts(
    underlying_ticker: Optional[str] = None,
    underlying_ticker_lt: Optional[str] = None,
    underlying_ticker_lte: Optional[str] = None,
    underlying_ticker_gt: Optional[str] = None,
    underlying_ticker_gte: Optional[str] = None,
    contract_type: Optional[str] = None,
    expiration_date: Optional[Union[str, date]] = None,
    expiration_date_lt: Optional[Union[str, date]] = None,
    expiration_date_lte: Optional[Union[str, date]] = None,
    expiration_date_gt: Optional[Union[str, date]] = None,
    expiration_date_gte: Optional[Union[str, date]] = None,
    as_of: Optional[Union[str, date]] = None,
    strike_price: Optional[float] = None,
    strike_price_lt: Optional[float] = None,
    strike_price_lte: Optional[float] = None,
    strike_price_gt: Optional[float] = None,
    strike_price_gte: Optional[float] = None,
    expired: Optional[bool] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    List and search options contracts with various filters.
    """
    try:
        results = polygon_client.list_options_contracts(
            underlying_ticker=underlying_ticker,
            underlying_ticker_lt=underlying_ticker_lt,
            underlying_ticker_lte=underlying_ticker_lte,
            underlying_ticker_gt=underlying_ticker_gt,
            underlying_ticker_gte=underlying_ticker_gte,
            contract_type=contract_type,
            expiration_date=expiration_date,
            expiration_date_lt=expiration_date_lt,
            expiration_date_lte=expiration_date_lte,
            expiration_date_gt=expiration_date_gt,
            expiration_date_gte=expiration_date_gte,
            as_of=as_of,
            strike_price=strike_price,
            strike_price_lt=strike_price_lt,
            strike_price_lte=strike_price_lte,
            strike_price_gt=strike_price_gt,
            strike_price_gte=strike_price_gte,
            expired=expired,
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


# ========================================
# Simplified Wrapper Tools for Common Use Cases
# ========================================
# These high-level tools make it easier for LLMs to quickly get
# common data without needing to understand all the parameters


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting latest price for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        from_date, to_date = _get_date_range_default(days_back)

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
        return _build_error_response(e, f"Getting daily bars for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
            market_type="stocks", direction=direction, include_otc=False, limit=limit
        )
    except Exception as e:
        return _build_error_response(e, f"Getting market {direction}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, context)


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting quote for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def check_market_open() -> Dict[str, Any]:
    """
    Check if the stock market is currently open (simplified).

    Quick way to see current market status and trading hours for all exchanges.
    Shows which markets are open/closed and their operating hours.

    Returns:
        JSON with market status, after/pre-market hours, and exchange-specific statuses

    Example Usage:
        - check_market_open() - Is the market open right now?

    Related Tools:
        - get_market_status: The underlying API this uses
        - get_market_holidays: See upcoming market holidays
    """
    try:
        return await get_market_status()
    except Exception as e:
        return _build_error_response(e, "Checking market status")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting snapshot for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_crypto_price(
    crypto: str = "BTC", currency: str = "USD"
) -> Dict[str, Any]:
    """
    Get current cryptocurrency price (simplified).

    Easy way to get crypto prices. Supports major cryptocurrencies against USD
    and other fiat currencies.

    Args:
        crypto: Cryptocurrency code (e.g., "BTC", "ETH", "LTC", "DOGE")
        currency: Fiat currency code (default: "USD", also supports "EUR", "GBP", etc.)

    Returns:
        JSON with latest crypto trade including price, size, timestamp

    Example Usage:
        - get_crypto_price("BTC") - Bitcoin in USD
        - get_crypto_price("ETH", "USD") - Ethereum in USD
        - get_crypto_price("BTC", "EUR") - Bitcoin in EUR

    Related Tools:
        - get_last_crypto_trade: The underlying API this uses
        - get_snapshot_ticker: Full crypto snapshot
        - get_aggs: Historical crypto price data
    """
    try:
        return await get_last_crypto_trade(from_=crypto, to=currency)
    except Exception as e:
        return _build_error_response(e, f"Getting {crypto}/{currency} price")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Getting company info for {ticker}")


@poly_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
        return _build_error_response(e, f"Searching for '{search_term}'")


# ========================================
# Server Startup
# ========================================

# Directly expose the MCP server object
# It will be run from entrypoint.py


def run(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Run the Polygon MCP server."""
    poly_mcp.run(transport)
