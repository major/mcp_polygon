"""Crypto-related endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict
from mcp.types import ToolAnnotations

from .helpers import build_error_response


def register_tools(mcp_server, polygon_client):
    """Register crypto-related tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
            return build_error_response(e, f"Getting {crypto}/{currency} price")
