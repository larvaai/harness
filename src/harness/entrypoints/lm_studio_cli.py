from __future__ import annotations

import argparse
import asyncio
import json
import sys

from harness.core.domain import RuntimeStatus, Task
from harness.runtime import build_lm_studio_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the harness core use case against LM Studio."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Reply with exactly: harness-ok",
        help="User task to send through RunTaskUseCase.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:1234/v1",
        help="OpenAI-compatible LM Studio base URL.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model id. If omitted, the first non-embedding model is used.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Optional response token cap.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum RunTaskUseCase LLM loop iterations.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List models reported by LM Studio and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final RunResult as JSON.",
    )
    parser.add_argument(
        "--show-trace",
        action="store_true",
        help="Print lifecycle event points and checkpoint reasons.",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    runtime = build_lm_studio_runtime(
        base_url=args.base_url,
        model=args.model,
        temperature=args.temperature,
        timeout_seconds=args.timeout,
        max_tokens=args.max_tokens,
        max_iterations=args.max_iterations,
    )

    if args.list_models:
        models = await runtime.llm.list_models()
        for model in models:
            print(model)
        return 0

    result = await runtime.run_task.execute(Task(args.prompt))

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"status: {result.status.value}")
        if result.final_answer:
            print("\nfinal_answer:")
            print(result.final_answer)
        if result.error:
            print("\nerror:", result.error)

    if args.show_trace:
        print("\ntrace:")
        for event in runtime.events.events:
            print(f"- event: {event.point.value}")
        for checkpoint in runtime.checkpoints.checkpoints:
            print(f"- checkpoint[{checkpoint.seq}]: {checkpoint.reason.value}")

    return 0 if result.status == RuntimeStatus.FINISHED else 1


def main() -> None:
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
