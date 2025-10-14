"""Forex-related endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict
from mcp.types import ToolAnnotations


def register_tools(mcp_server, polygon_client):
    """Register forex-related tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
