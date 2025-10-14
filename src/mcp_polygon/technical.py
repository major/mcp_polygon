"""Technical indicators endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict, Union
from datetime import datetime, date
from mcp.types import ToolAnnotations


def register_tools(mcp_server, polygon_client):
    """Register technical indicator tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
