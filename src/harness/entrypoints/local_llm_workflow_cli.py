from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from harness.core.domain import LocalWorkflowState
from harness.runtime import build_local_llm_workflow_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the staged local-LLM workflow against LM Studio."
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=(
            "Analyze the local_llm docs and current code, then report what the "
            "read-only workflow should do."
        ),
        help="Task to run through the local LLM workflow.",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root used by the context retriever.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:1234/v1",
        help="OpenAI-compatible LM Studio base URL.",
    )
    parser.add_argument("--model", default=None, help="LM Studio model id.")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-context-items", type=int, default=8)
    parser.add_argument(
        "--textlog-name",
        default="local_llm",
        help="Directory name under var/ for the human-readable LLM text log.",
    )
    parser.add_argument(
        "--textlog-path",
        default=None,
        help="Explicit path for the human-readable LLM text log.",
    )
    parser.add_argument(
        "--no-textlog",
        action="store_true",
        help="Disable the human-readable LLM text log.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full LocalWorkflowResult as JSON.",
    )
    parser.add_argument(
        "--show-raw",
        action="store_true",
        help="Print raw model output for each worker.",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    text_log_path = _text_log_path(args)
    runtime = build_local_llm_workflow_runtime(
        workspace_root=args.workspace_root,
        base_url=args.base_url,
        model=args.model,
        temperature=args.temperature,
        timeout_seconds=args.timeout,
        max_tokens=args.max_tokens,
        max_context_items=args.max_context_items,
        text_log_path=text_log_path,
    )
    result = await runtime.run_workflow.execute(args.task)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"state: {result.state.value}")
        if result.task_spec:
            print(f"\ngoal: {result.task_spec.goal}")
        if result.context_pack:
            print(f"context_items: {len(result.context_pack.items)}")
        if result.fact_set:
            print(f"facts: {len(result.fact_set.facts)}")
        if result.plan:
            print(f"plan_steps: {len(result.plan.plan)}")
        if result.final_report:
            print("\nsummary:")
            print(result.final_report.summary)
        if result.error:
            print("\nerror:")
            print(result.error)

    if runtime.text_log_path is not None:
        print(f"\nllm_textlog: {runtime.text_log_path}")

    if args.show_raw:
        print("\nraw_outputs:")
        for name, raw in result.raw_outputs.items():
            print(f"\n--- {name} ---")
            print(raw)

    return 0 if result.state == LocalWorkflowState.COMPLETED else 1


def _text_log_path(args: argparse.Namespace) -> Path | None:
    if args.no_textlog:
        return None
    if args.textlog_path:
        return Path(args.textlog_path)
    return Path("var") / args.textlog_name / "llm-textlog.txt"


def main() -> None:
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
