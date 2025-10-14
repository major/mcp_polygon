"""Helper functions for the Polygon MCP server."""

from typing import Any, Dict, Union
from datetime import datetime, date, timedelta


def validate_ticker(ticker: str) -> bool:
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


def format_date_for_api(date_input: Union[str, datetime, date]) -> str:
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


def get_date_range_default(days_back: int = 30) -> tuple[str, str]:
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


def build_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
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
