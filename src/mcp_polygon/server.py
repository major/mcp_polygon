"""Main server module for the Polygon MCP server."""

import os
from typing import Literal
from mcp.server.fastmcp import FastMCP
from polygon import RESTClient
from importlib.metadata import version, PackageNotFoundError

# Import all endpoint modules
from . import stocks
from . import options
from . import crypto
from . import forex
from . import futures
from . import market
from . import reference
from . import technical
from . import benzinga

# ========================================
# Initialize Polygon API Client
# ========================================

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

# ========================================
# Initialize MCP Server
# ========================================

poly_mcp = FastMCP("Polygon", dependencies=["polygon"])

# ========================================
# Register Tools from Modules
# ========================================

# Register all tools from each module
stocks.register_tools(poly_mcp, polygon_client)
options.register_tools(poly_mcp, polygon_client)
crypto.register_tools(poly_mcp, polygon_client)
forex.register_tools(poly_mcp, polygon_client)
futures.register_tools(poly_mcp, polygon_client)
market.register_tools(poly_mcp, polygon_client)
reference.register_tools(poly_mcp, polygon_client)
technical.register_tools(poly_mcp, polygon_client)
benzinga.register_tools(poly_mcp, polygon_client)

# ========================================
# Server Startup
# ========================================


def run(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Run the Polygon MCP server."""
    poly_mcp.run(transport)
