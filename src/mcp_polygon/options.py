"""Options-related endpoints for the Polygon MCP server."""

import json
from typing import Optional, Any, Dict, Union
from datetime import date
from mcp.types import ToolAnnotations


def register_tools(mcp_server, polygon_client):
    """Register options-related tools with the MCP server."""

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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

    @mcp_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
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
