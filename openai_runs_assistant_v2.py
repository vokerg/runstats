import argparse
import asyncio
import json
import os
import logging
from datetime import date
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[ASSISTANT V2] %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/runstats.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


DEFAULT_URL = "http://127.0.0.1:8000/mcp"
DEFAULT_MODEL = "gpt-5.4-nano"
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"


QUERY_RUNS_TOOL = {
    "type": "function",
    "name": "query_runs",
    "description": (
        "Query run records from the user's MCP runs service v2. Use this whenever the "
        "user asks about run history, records, trends, dates, types, distances, or rankings. "
        "Supports filtering by distance, run type, date range, year, and various ranking columns."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "distance_km": {
                "type": "number",
                "description": "Exact distance in kilometers (e.g., 5, 10, 21.1, 42.2). Omit or use 0 to search all distances.",
            },
            "run_type": {
                "type": "string",
                "enum": ["outdoor", "track", "treadmill"],
                "description": "Optional run type filter. Omit when not needed. Use 'outdoor' for outdoor runs, 'track' for track/stadium runs, 'treadmill' for treadmill runs.",
            },
            "year": {
                "type": "integer",
                "description": "Filter by specific year (e.g., 2023, 2024). Omit when unknown or not needed. Do not send 0.",
            },
            "date_from": {
                "type": "string",
                "description": "Inclusive start date in YYYY-MM-DD format. Omit when not needed; do not send an empty string.",
            },
            "date_to": {
                "type": "string",
                "description": "Inclusive end date in YYYY-MM-DD format. Omit when not needed; do not send an empty string.",
            },
            "rank_all": {
                "type": "integer",
                "description": "Filter to runs with this overall rank across all surfaces (1=fastest overall for that distance). Use 0 or omit to skip filtering.",
            },
            "rank_outdoor_track": {
                "type": "integer",
                "description": "Filter to runs with this rank among outdoor and track runs only (excludes treadmill). Use 0 or omit to skip filtering.",
            },
            "rank_track": {
                "type": "integer",
                "description": "Filter to runs with this rank among track runs only. Use 0 or omit to skip filtering.",
            },
            "rank_treadmill": {
                "type": "integer",
                "description": "Filter to runs with this rank among treadmill runs only. Use 0 or omit to skip filtering.",
            },
            "is_record": {
                "type": "integer",
                "enum": [0, 1],
                "description": "1 for personal records only (fastest overall for that distance), 0 for non-records. Omit to include both.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return. Defaults to 100, max 1000. Use limit=1 to get just the best result.",
            },
        },
        "additionalProperties": False,
    },
}


def extract_tool_payload(result: object) -> dict[str, Any]:
    content = getattr(result, "content", None) or []
    payload_text = ""
    if content:
        payload_text = getattr(content[0], "text", "") or ""

    if not payload_text:
        return {}

    try:
        return json.loads(payload_text)
    except json.JSONDecodeError:
        return {"raw_text": payload_text}


def build_instructions(today: str) -> str:
    return (
        "You are a running-data assistant with access to a comprehensive runs database. "
        "Always ground claims in tool results from the user's MCP runs service, and never invent run records. "
        "Use the query_runs tool whenever the answer depends on run data. The current date is "
        f"{today}. When the user uses relative dates like 'recently' or 'last year', "
        "interpret them relative to that date. "
        "You can filter by distance (5km, 10km, etc), run type (outdoor, track, treadmill), year, date range, and rankings. "
        "Only filter by run_type when the user explicitly asks for outdoor, track, or treadmill results. "
        "When calling query_runs, omit filters you do not need instead of sending placeholder values. "
        "Do not send year=0, and do not send empty strings for date_from/date_to. "
        "For meaningful comparisons, prefer rank_outdoor_track (outdoor+track combined) over rank_all when the user cares about 'real' outdoor performance. "
        "For questions like 'fastest ever' at a specific distance, query that exact distance with limit=1 and no year filter unless the user asks for a year. "
        "In your final answer, be concise, cite specific dates and times when helpful, include the run's speed/pace if available, "
        "and clearly indicate the run type if relevant."
    )


def sanitize_query_runs_args(tool_args: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(tool_args)

    if cleaned.get("year") in (0, "", None):
        cleaned.pop("year", None)
    if cleaned.get("date_from") in ("", None):
        cleaned.pop("date_from", None)
    if cleaned.get("date_to") in ("", None):
        cleaned.pop("date_to", None)
    if cleaned.get("run_type") in ("", None):
        cleaned.pop("run_type", None)

    return cleaned


def build_transport(args: argparse.Namespace):
    if args.transport == "stdio":
        # Cross-platform Python executable path in virtual environment
        if os.name == 'nt':  # Windows
            python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        else:  # Unix-like
            python_exe = PROJECT_ROOT / ".venv" / "bin" / "python"
        
        logger.info(f"🔌 Starting MCP server v2 via stdio: {python_exe}")
        server = StdioServerParameters(
            command=str(python_exe),
            args=["runs_mcp_server_v2.py"],
            cwd=str(PROJECT_ROOT),
        )
        return stdio_client(server)
    logger.info(f"🔌 Connecting to MCP server via HTTP: {args.url}")
    return streamable_http_client(args.url)


def load_environment() -> None:
    load_dotenv(ENV_PATH)


async def ask_question(
    *,
    client: OpenAI,
    session: ClientSession,
    model: str,
    instructions: str,
    question: str,
    max_output_tokens: int,
    max_round_trips: int,
    verbose: bool,
    previous_response_id: str | None = None,
) -> tuple[str, str]:
    logger.info(f"❓ User question: {question}")
    
    response = client.responses.create(
        model=model,
        input=question,
        previous_response_id=previous_response_id,
        instructions=instructions,
        tools=[QUERY_RUNS_TOOL],
        tool_choice="auto",
        parallel_tool_calls=False,
        max_output_tokens=max_output_tokens,
    )
    logger.info(f"🤖 OpenAI API response received")

    for round_num in range(max_round_trips):
        function_calls = [
            item for item in response.output if getattr(item, "type", None) == "function_call"
        ]
        if not function_calls:
            answer = response.output_text.strip()
            logger.info(f"✅ Final answer: {answer[:100]}..." if len(answer) > 100 else f"✅ Final answer: {answer}")
            return answer, response.id

        logger.info(f"🔄 Round {round_num + 1}: Found {len(function_calls)} tool call(s)")
        
        tool_outputs = []
        for item in function_calls:
            tool_args = json.loads(item.arguments or "{}")
            if item.name == "query_runs":
                sanitized_args = sanitize_query_runs_args(tool_args)
                if sanitized_args != tool_args:
                    logger.info(
                        "   Sanitized query_runs args from %s to %s",
                        json.dumps(tool_args),
                        json.dumps(sanitized_args),
                    )
                tool_args = sanitized_args
            logger.info(f"   📞 Calling: {item.name}({json.dumps(tool_args)})")
            
            tool_result = await session.call_tool(item.name, tool_args)
            payload = extract_tool_payload(tool_result)

            logger.info(f"   ✔️ {item.name}() returned {len(payload.get('rows', []))} row(s)" if 'rows' in payload else f"   ✔️ {item.name}() response: {payload}")

            if verbose:
                print()
                print(f"[tool] {item.name}({json.dumps(tool_args)})")
                print(json.dumps(payload, indent=2))

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(payload),
                }
            )

        response = client.responses.create(
            model=model,
            previous_response_id=response.id,
            input=tool_outputs,
            instructions=instructions,
            tools=[QUERY_RUNS_TOOL],
            tool_choice="auto",
            parallel_tool_calls=False,
            max_output_tokens=max_output_tokens,
        )
        logger.info(f"🤖 OpenAI API processed tool results")

    raise RuntimeError("The assistant exceeded the maximum number of tool round-trips.")


async def run_single_question(args: argparse.Namespace) -> str:
    logger.info("🚀 Starting single question mode...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env or export it in your shell."
        )

    client = OpenAI(api_key=api_key)
    logger.info("✅ OpenAI client initialized")
    transport_cm = build_transport(args)
    instructions = build_instructions(args.today)

    async with transport_cm as (read_stream, write_stream, *_rest):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            logger.info("✅ MCP session initialized")
            answer, _response_id = await ask_question(
                client=client,
                session=session,
                model=args.model,
                instructions=instructions,
                question=args.question,
                max_output_tokens=args.max_output_tokens,
                max_round_trips=args.max_round_trips,
                verbose=args.verbose,
            )
            return answer


async def run_chat_loop(args: argparse.Namespace) -> None:
    logger.info("🚀 Starting chat mode...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env or export it in your shell."
        )

    client = OpenAI(api_key=api_key)
    logger.info("✅ OpenAI client initialized")
    transport_cm = build_transport(args)
    instructions = build_instructions(args.today)

    async with transport_cm as (read_stream, write_stream, *_rest):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            logger.info("✅ MCP session initialized and ready")
            previous_response_id = None

            print(f"Runs chat v2 is ready with model {args.model}.")
            print("Type a question, or 'exit' to quit.")
            print("Examples: 'What was my fastest 5k outdoor run in 2023?'")
            print("          'Show my top 3 10k times.'")
            print("          'How many PRs did I set last year?'")

            while True:
                try:
                    question = input("\nYou: ").strip()
                except EOFError:
                    print()
                    logger.info("👋 Chat ended (EOF)")
                    return

                if not question:
                    continue
                if question.lower() in {"exit", "quit"}:
                    logger.info("👋 Chat ended (user requested exit)")
                    return

                try:
                    answer, previous_response_id = await ask_question(
                        client=client,
                        session=session,
                        model=args.model,
                        instructions=instructions,
                        question=question,
                        max_output_tokens=args.max_output_tokens,
                        max_round_trips=args.max_round_trips,
                        verbose=args.verbose,
                        previous_response_id=previous_response_id,
                    )
                except RuntimeError as exc:
                    logger.error(f"âŒ Chat turn failed: {exc}")
                    print(f"\nAssistant: Sorry, I got stuck while querying your runs: {exc}")
                    previous_response_id = None
                    continue

                print(f"\nAssistant: {answer}")


async def run_assistant(args: argparse.Namespace) -> str | None:
    if args.chat:
        await run_chat_loop(args)
        return None
    return await run_single_question(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask plain-English questions about your run history using OpenAI plus MCP runs service v2."
    )
    parser.add_argument("question", nargs="?", help="Natural-language question about your runs.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="How to connect to the MCP server.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="MCP streamable HTTP endpoint.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenAI model to use. Defaults to the current low-cost GPT-5 option.",
    )
    parser.add_argument(
        "--today",
        default=date.today().isoformat(),
        help="Reference date for relative time phrases. Defaults to the current local date.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=500,
        help="Upper bound for generated output tokens.",
    )
    parser.add_argument(
        "--max-round-trips",
        type=int,
        default=6,
        help="Maximum number of tool-call rounds before stopping.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print MCP tool calls and payloads before the final answer.",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start an interactive chat so you can ask follow-up questions in one session.",
    )
    return parser.parse_args()


def main() -> None:
    load_environment()
    logger.info("📋 Loaded environment variables")
    
    args = parse_args()
    logger.info(f"⚙️ Configuration: transport={args.transport}, model={args.model}, chat={args.chat}")
    
    if not args.question and not args.chat:
        args.chat = True

    try:
        answer = asyncio.run(run_assistant(args))
    except RuntimeError as exc:
        logger.error(f"❌ Error: {exc}")
        raise SystemExit(str(exc))

    if answer is not None:
        print()
        print(answer)


if __name__ == "__main__":
    main()
