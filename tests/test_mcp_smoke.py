import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_server_exposes_all_tools():
    params = StdioServerParameters(
        command=".venv/bin/python", args=["-m", "src.server"], cwd=".",
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert len(names) == 60
            assert {"search_stocks", "get_index_constituents", "get_stock_quote"} <= names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_nse_search_and_nifty_constituents():
    params = StdioServerParameters(
        command=".venv/bin/python", args=["-m", "src.server"], cwd=".",
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            search = await session.call_tool("search_stocks", {"query": "RELIANCE"})
            constituents = await session.call_tool("get_index_constituents", {"index": "NIFTY 50"})
            assert "RELIANCE" in str(search.content)
            assert '"count": 50' in str(constituents.content)
