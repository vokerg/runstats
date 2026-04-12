import argparse
import asyncio
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI
from dotenv import load_dotenv


DEFAULT_URL = "http://127.0.0.1:8000/mcp"
DEFAULT_MODEL = "gpt-5.4-nano"
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"


GET_RUNS_TOOL = {
    "type": "function",
    "name": "get_runs",
    "description": (
        "Fetch run records from the user's MCP runs service. Use this whenever the "
        "user asks about run history, records, trends, dates, types, or distances."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "distance_km": {
                "type": "number",
                "description": "Exact distance in kilometers, such as 5, 10, 21.1, or 42.2.",
            },
            "run_type": {
                "type": "string",
                "enum": ["outdoor", "track", "treadmill"],
                "description": "Optional run type filter.",
            },
            "date_from": {
                "type": "string",
                "description": "Inclusive start date in YYYY-MM-DD format.",
            },
            "date_to": {
                "type": "string",
                "description": "Inclusive end date in YYYY-MM-DD format.",
            },
            "rank_all": {
                "type": "integer",
                "description": "Select runs where overall rank equals this value.",
            },
            "rank_outdoor": {
                "type": "integer",
                "description": "Select runs where outdoor rank equals this value.",
            },
            "is_record": {
                "type": "integer",
                "enum": [0, 1],
                "description": "1 for records only, 0 for non-records only.",
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
        "You are a running-data assistant. Always ground claims in tool results from the "
        "user's MCP runs service, and never invent run records. Use the get_runs tool "
        "whenever the answer depends on run data. The current date is "
        f"{today}. When the user uses relative dates like 'recently' or 'last year', "
        "interpret them relative to that date. In your final answer, be concise, cite "
        "specific dates and times when helpful, and say clearly if the data is "
        "insufficient."
    )


def build_transport(args: argparse.Namespace):
    if args.transport == "stdio":
        server = StdioServerParameters(
            command=str(PROJECT_ROOT / ".venv" / "bin" / "python"),
            args=["runs_mcp_server.py"],
            cwd=str(PROJECT_ROOT),
        )
        return stdio_client(server)
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
    response = client.responses.create(
        model=model,
        input=question,
        previous_response_id=previous_response_id,
        instructions=instructions,
        tools=[GET_RUNS_TOOL],
        tool_choice="auto",
        parallel_tool_calls=False,
        max_output_tokens=max_output_tokens,
    )

    for _ in range(max_round_trips):
        function_calls = [
            item for item in response.output if getattr(item, "type", None) == "function_call"
        ]
        if not function_calls:
            return response.output_text.strip(), response.id

        tool_outputs = []
        for item in function_calls:
            tool_args = json.loads(item.arguments or "{}")
            tool_result = await session.call_tool(item.name, tool_args)
            payload = extract_tool_payload(tool_result)

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
            tools=[GET_RUNS_TOOL],
            tool_choice="auto",
            parallel_tool_calls=False,
            max_output_tokens=max_output_tokens,
        )

    raise RuntimeError("The assistant exceeded the maximum number of tool round-trips.")


async def run_single_question(args: argparse.Namespace) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env or export it in your shell."
        )

    client = OpenAI(api_key=api_key)
    transport_cm = build_transport(args)
    instructions = build_instructions(args.today)

    async with transport_cm as (read_stream, write_stream, *_rest):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
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
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env or export it in your shell."
        )

    client = OpenAI(api_key=api_key)
    transport_cm = build_transport(args)
    instructions = build_instructions(args.today)

    async with transport_cm as (read_stream, write_stream, *_rest):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            previous_response_id = None

            print(f"Runs chat is ready with model {args.model}.")
            print("Type a question, or 'exit' to quit.")

            while True:
                try:
                    question = input("\nYou: ").strip()
                except EOFError:
                    print()
                    return

                if not question:
                    continue
                if question.lower() in {"exit", "quit"}:
                    return

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
                print(f"\nAssistant: {answer}")


async def run_assistant(args: argparse.Namespace) -> str | None:
    if args.chat:
        await run_chat_loop(args)
        return None
    return await run_single_question(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask plain-English questions about your run history using OpenAI plus your MCP server."
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
    args = parse_args()
    if not args.question and not args.chat:
        args.chat = True

    try:
        answer = asyncio.run(run_assistant(args))
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    if answer is not None:
        print()
        print(answer)


if __name__ == "__main__":
    main()
