import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client


DEFAULT_URL = "http://127.0.0.1:8000/mcp"
PROJECT_ROOT = Path(__file__).resolve().parent


def extract_rows(result: object) -> list[dict]:
    content = getattr(result, "content", None) or []
    payload_text = ""
    if content:
        first_item = content[0]
        payload_text = getattr(first_item, "text", "")

    payload = json.loads(payload_text) if payload_text else {"rows": []}
    return payload.get("rows", [])


async def main() -> None:
    parser = argparse.ArgumentParser(description="Small MCP client for the runs server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="How to connect to the MCP server.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="MCP streamable HTTP endpoint.")
    parser.add_argument("--distance", type=float, default=5.0, help="Distance filter in km.")
    parser.add_argument("--limit", type=int, default=5, help="How many rows to print.")
    parser.add_argument("--type", dest="run_type", help="Optional run type filter.")
    parser.add_argument("--records-only", action="store_true", help="Only fetch record runs.")
    args = parser.parse_args()

    if args.transport == "stdio":
        server = StdioServerParameters(
            command=str(PROJECT_ROOT / ".venv" / "bin" / "python"),
            args=["runs_mcp_server.py"],
            cwd=str(PROJECT_ROOT),
        )
        transport_cm = stdio_client(server)
    else:
        transport_cm = streamable_http_client(args.url)

    async with transport_cm as (read_stream, write_stream, *_rest):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print(f"- {tool.name}")

            result = await session.call_tool(
                "get_runs",
                {
                    "distance_km": args.distance,
                    "run_type": args.run_type,
                    "is_record": 1 if args.records_only else None,
                },
            )
            rows = extract_rows(result)

            print()
            print(f"Returned {len(rows)} rows")
            print(json.dumps(rows[: args.limit], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
