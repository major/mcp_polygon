"""Market status and holidays endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict
from mcp.types import ToolAnnotations

from .helpers import build_error_response


def register_tools(mcp_server, polygon_client):
    """Register market status/holidays tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
            return build_error_response(e, "Getting market status")

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
            return build_error_response(e, "Checking market status")
