"""Run paired source-review evaluations; retain every attempt and failure."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent import make_agent
from tools import RepositoryTools
from tools.report import ReportTool

ROOT = Path(__file__).parent
MODEL = "gemini-3.5-flash-lite"
QUESTION = "Review app.py and relevant helpers for supported security issues."
# Standard paid rates checked 2026-11-11, USD per million tokens.
INPUT_RATE, OUTPUT_RATE = 0.30, 2.50
# Conservative per-call reservation, including unknown usage after failures.
RESERVE = 0.05


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Budget:
    def __init__(self, path, cap):
        self.path, self.cap = path, cap
        self.data = json.loads(path.read_text()) if path.exists() else {
            "estimated_usd": 0, "calls_reserved": 0, "attempts": 0,
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2) + "\n")

    def reserve(self):
        if self.data["estimated_usd"] + RESERVE > self.cap:
            raise RuntimeError("Aggregate cost cap reached")
        self.data["estimated_usd"] += RESERVE
        self.data["calls_reserved"] += 1
        self.save()

    def settle(self, usage):
        if usage is None:
            return
        prompt = usage.prompt_token_count
        output = usage.candidates_token_count
        if prompt is None or output is None:
            return
        cost = (prompt * INPUT_RATE + (
            output + (usage.thoughts_token_count or 0)
        ) * OUTPUT_RATE) / 1_000_000
        # Never refund when reported usage exceeds the reservation.
        self.data["estimated_usd"] += max(cost, 0) - RESERVE
        self.save()


async def run_case(case, arm, attempt, budget, output_dir, key):
    source = RepositoryTools(ROOT / "fixtures" / case["id"])
    if source.omitted or set(source.files) != set(case["files"]):
        raise ValueError("Fixture selection lost files")
    for name, expected in case["files"].items():
        if hashlib.sha256(source.files[name].encode()).hexdigest() != expected:
            raise ValueError("Fixture changed after manifest freeze")
    reporter = ReportTool(source)
    agent = make_agent(source, MODEL, key)
    agent.tools.append(reporter.submit_report)
    agent.instruction += "\n" + (ROOT / "prompts/report.txt").read_text()
    if arm == "context":
        agent.instruction += "\n" + (ROOT / "prompts/context.txt").read_text()
    question = QUESTION
    max_calls = 8
    if arm == "single":
        agent.tools = [reporter.submit_report]
        agent.instruction = agent.instruction.replace(
            "Discover files with your tools, then follow input to sensitive operations.",
            "Read the supplied complete source, then follow input to sensitive operations."
        ).replace("You have at most 8 model calls;", "You have one model call;")
        question += "\nAll available source follows, with line numbers:\n"
        for name in sorted(source.files):
            question += "\nFILE " + name + "\n"
            question += "\n".join(f"{i}: {line}" for i, line in
                                  enumerate(source.lines(name), 1)) + "\n"
        max_calls = 1
    trace = []
    usages = []
    calls = 0

    async def before_model(callback_context, llm_request):
        nonlocal calls
        if calls >= max_calls:
            raise RuntimeError("Model call cap reached before request")
        # Bound serialized content/config, plus ample schema/protocol margin.
        wire = llm_request.model_dump_json(exclude={"tools_dict"})
        if len(wire.encode()) > 50_000:
            raise RuntimeError("Request size cap reached")
        wait = max(0, budget.data.get("last_request_at", 0) + 4.5 - time.time())
        await asyncio.sleep(wait)
        budget.reserve()
        budget.data["last_request_at"] = time.time()
        budget.save()
        calls += 1

    def after_model(callback_context, llm_response):
        usage = llm_response.usage_metadata
        budget.settle(usage)
        usages.append(usage.model_dump(mode="json") if usage else None)

    agent.before_model_callback = before_model
    agent.after_model_callback = after_model
    runner = InMemoryRunner(agent=agent, app_name="code_reviewer")
    started = time.monotonic()
    status, error = "incomplete", None
    result = {
        "case": case["id"], "arm": arm, "attempt": attempt,
        "model": MODEL, "started_at": datetime.now(timezone.utc).isoformat(),
        "instruction_sha256": hashlib.sha256(agent.instruction.encode()).hexdigest(),
        "manifest_sha256": digest(ROOT / "manifest.json"),
        "max_model_calls": max_calls, "timeout_seconds": 120,
        "minimum_call_spacing_seconds": 4.5,
    }
    path = output_dir / f'{case["id"]}-{arm}-{attempt}.json'
    if path.exists():
        raise FileExistsError(path)
    budget.data["attempts"] += 1
    budget.save()
    result["status"] = "started"
    path.write_text(json.dumps(result, indent=2) + "\n")
    try:
        session = await runner.session_service.create_session(
            app_name="code_reviewer", user_id="reviewer",
        )
        async with asyncio.timeout(120):
            events = runner.run_async(
                user_id="reviewer", session_id=session.id,
                new_message=types.Content(
                    role="user", parts=[types.Part.from_text(text=question)],
                ),
                run_config=RunConfig(max_llm_calls=max_calls),
            )
            async for event in events:
                trace.append(event.model_dump(mode="json", exclude_none=True))
                if event.error_code:
                    error = str(event.error_code)
                    break
                if reporter.accepted is not None:
                    status = "accepted"
                    break
            await events.aclose()
    except Exception as exc:
        error = type(exc).__name__
    finally:
        await runner.close()
    result.update({
        "status": status, "error": error, "report": reporter.accepted,
        "latency_seconds": round(time.monotonic() - started, 3),
        "model_calls": calls, "usage": usages, "trace": trace,
    })
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f'{case["id"]} {arm} #{attempt}: {status}, '
          f'{calls} calls, {result["latency_seconds"]}s', flush=True)
    return result


async def main(args):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key and args.key_file:
        # Read only the named local credential; never log it or copy it.
        from dotenv import dotenv_values
        key = dotenv_values(args.key_file).get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY or provide --key-file.")
    manifest = json.loads((ROOT / "manifest.json").read_text())
    cases = [c for c in manifest["cases"] if c["split"] == args.split]
    if args.smoke:
        cases = cases[:2]
    output = ROOT / "runs" / args.batch
    output.mkdir(parents=True, exist_ok=True)
    budget = Budget(ROOT / "runs/budget.json", args.max_usd)
    for attempt in range(1, args.attempts + 1):
        for i, case in enumerate(cases):
            # Alternate paired execution order; do not favor one with time.
            arms = args.arms
            if (i + attempt) % 2 == 0:
                arms = list(reversed(arms))
            for arm in arms:
                if (output / f'{case["id"]}-{arm}-{attempt}.json').exists():
                    continue
                if budget.data["attempts"] >= 48:
                    print("48-attempt cap reached.")
                    return
                if budget.data["estimated_usd"] + RESERVE > budget.cap:
                    print("Cost cap reached; remaining cases are not run.")
                    return
                result = await run_case(case, arm, attempt, budget, output, key)
                if args.smoke and result["status"] != "accepted":
                    print("Smoke stopped; inspect the recorded failure.")
                    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--max-usd", type=float, default=5)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--arms", nargs="+", choices=["baseline", "context", "single"],
                        default=["baseline", "context"])
    parser.add_argument("--key-file", type=Path)
    asyncio.run(main(parser.parse_args()))
