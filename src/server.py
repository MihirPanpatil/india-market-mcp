"""India Market MCP — Comprehensive Indian Stock Market MCP Server.

Covers: NSE/BSE Stocks, F&O Derivatives, Mutual Funds, Indices,
Market Overview, Technical Analysis, ETFs, Commodities, Currencies,
SGBs, IPOs, FII/DII Data, and Stock Screening.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "India Market MCP",
    instructions="Comprehensive MCP server for Indian stock market — NSE, BSE, Mutual Funds, F&O, Technicals, ETFs, Commodities, Currencies, Screeners",
)

# Register all modules — handle both package import and direct script execution
import sys
import os

try:
    _here = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _here = os.path.join(os.getcwd(), "src")

_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

from src.modules.stocks import register as reg_stocks
from src.modules.derivatives import register as reg_derivatives
from src.modules.indices import register as reg_indices
from src.modules.mutual_funds import register as reg_mutual_funds
from src.modules.market import register as reg_market
from src.modules.technicals import register as reg_technicals
from src.modules.additional import register as reg_additional

reg_stocks(mcp)
reg_derivatives(mcp)
reg_indices(mcp)
reg_mutual_funds(mcp)
reg_market(mcp)
reg_technicals(mcp)
reg_additional(mcp)


def main():
    """Entry point for india-market-mcp command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
