# Level 1 Code Index MCP Server

Server nay expose code index read-only qua MCP stdio. Muc Level 1 gom:

- `code_index.list_files`: liet ke file text trong workspace.
- `code_index.search_text`: tim text case-insensitive va tra ve file/line/context.
- `code_index.read_file`: doc file theo path tuong doi workspace va line range.

MCP server nay chi la wrapper cho feature tools. Moi `tools/call` phai di qua `ExecuteToolCallUseCase`, `BEFORE_TOOL` hook va `AFTER_TOOL` hook.

## Chay truc tiep

Tu repo root:

```bash
PYTHONPATH=src python -m harness.entrypoints.code_index_mcp_server --workspace-root .
```

Neu package da duoc install, co the dung script:

```bash
harness-code-index-mcp --workspace-root /absolute/path/to/workspace
```

Server dung stdio, vi vay stdout chi duoc ghi JSON-RPC message. Log va loi startup duoc ghi qua stderr.

## MCP client config mau

```json
{
  "mcpServers": {
    "harness-code-index": {
      "command": "python",
      "args": [
        "-m",
        "harness.entrypoints.code_index_mcp_server",
        "--workspace-root",
        "/Users/uspro/Desktop/Namson/harness_practice"
      ],
      "env": {
        "PYTHONPATH": "/Users/uspro/Desktop/Namson/harness_practice/src"
      }
    }
  }
}
```

## Tool output

Moi tool tra ca:

- `content`: JSON dang text de client/LLM doc duoc.
- `structuredContent`: object goc de client parse truc tiep.
- `isError`: `false` neu tool thanh cong, `true` neu loi thuc thi nhu path khong hop le.

## Gioi han Level 1

- Chua co symbols/imports/signatures.
- Chua co call graph hoac references chinh xac.
- `search_text` la text search co ranking nhe, khong phai semantic search.
- Binary/cache/generated files bi bo qua.
