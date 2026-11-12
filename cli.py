"""Run a small repository review and display the visible agent loop."""
import argparse
import asyncio
import json
import os
from pathlib import Path

from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent import make_agent
from tools import RepositoryTools

QUESTION = (
    "Review this repository for security vulnerabilities. "
    "Report findings with source evidence, suggested fixes, "
    "and the limitations of your review."
)


def show(label, value):
    print(f"\n--- {label} ---", flush=True)
    if not isinstance(value, str):
        value = json.dumps(value, indent=2, ensure_ascii=False)
    print(value, flush=True)


async def review(agent, question, max_calls=8, emit=show):
    runner = InMemoryRunner(agent=agent, app_name="code_reviewer")
    completed = False
    failed = False
    try:
        session = await runner.session_service.create_session(
            app_name="code_reviewer", user_id="reviewer",
        )
        async with asyncio.timeout(120):
            async for event in runner.run_async(
                user_id="reviewer",
                session_id=session.id,
                new_message=types.Content(
                    role="user", parts=[types.Part.from_text(text=question)],
                ),
                run_config=RunConfig(max_llm_calls=max_calls),
            ):
                for call in event.get_function_calls():
                    emit(f"TOOL CALL: {call.name}", call.args)
                for result in event.get_function_responses():
                    emit(f"TOOL RESULT: {result.name}", result.response)
                if event.error_code:
                    failed = True
                    emit("ERROR", event.error_code)
                if event.is_final_response() and event.content:
                    answer = "\n".join(
                        p.text for p in event.content.parts or []
                        if p.text and not p.thought
                    ).strip()
                    if answer:
                        emit("FINAL ANSWER", answer)
                        completed = True
    except Exception as error:
        # Avoid echoing provider messages that could contain credentials.
        failed = True
        emit("ERROR", f"{type(error).__name__}: review did not complete.")
    finally:
        await runner.close()
    success = completed and not failed
    emit("STATUS", "completed" if success else "incomplete")
    return success


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repo", nargs="?", type=Path,
        default=Path(__file__).parent / "sample",
    )
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument(
        "--model", default=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    )
    args = parser.parse_args()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        parser.error("Set GEMINI_API_KEY to run live reviews.")
    try:
        tools = RepositoryTools(args.repo)
    except (OSError, ValueError):
        parser.error("Choose an accessible local repository directory.")
    show("MODE", "LIVE GEMINI")
    show("SOURCE", "Selected source excerpts appear here and go to the model.")
    agent = make_agent(tools, args.model, key)
    return 0 if asyncio.run(review(agent, args.question)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
