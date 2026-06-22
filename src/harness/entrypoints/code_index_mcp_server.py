from __future__ import annotations

import argparse
import sys

from harness.features.code_index import CodeIndexMCPServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the read-only Level 1 code index MCP server over stdio."
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root to expose through the read-only code index.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        CodeIndexMCPServer.for_workspace(
            workspace_root=args.workspace_root,
        ).run_stdio()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:
        print(f"code-index-mcp-server failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
