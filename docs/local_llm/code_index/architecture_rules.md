# Code Index Architecture Rules

Doc nay la guardrail bat buoc truoc khi phat trien `code_index`.

## Luat phai doc truoc khi code

Truoc khi sua hoac nang cap code index, phai doc:

1. `docs/agent-harness-layered-build-guide.md`
2. `docs/local_llm/code_index/architecture_rules.md`
3. `docs/local_llm/code_index/implementation_plan.md`

Neu thay doi lien quan MCP, tool execution, hook, skill/plugin loading thi phai doc them file test hien co quanh:

- `tests/core/test_run_task_use_case.py`
- `tests/core/test_lifecycle_manager.py`
- `tests/code_index/`

## Quyet dinh kien truc

`code_index` la mot feature/skill/tool cua agent. No khong phai core.

Viec nay co nghia:

- Khong them `CodeIndex*` domain object vao `src/harness/core/domain/`.
- Khong them `CodeIndex*` port vao `src/harness/core/ports/`.
- Core chi duoc biet cac khai niem tong quat nhu `ToolDefinition`, `ToolCall`, `ToolResult`, `HookPoint`, `HookContext`, `HookResult`.
- Code index phai nam trong `src/harness/features/code_index/`.
- MCP server chi la wrapper/entrypoint de expose tool cua feature, khong duoc bypass tool lifecycle.

## Feature layout mong muon

```text
src/harness/features/code_index/
  skill.yaml
  instructions.md
  __init__.py
  domain.py
  ports.py
  filesystem_indexer.py
  tools.py
  hooks.py
  mcp_server.py
```

Trong do:

- `skill.yaml`: manifest de runtime/plugin loader sau nay co the discover tool/hook/policy.
- `instructions.md`: huong dan ngan cho agent khi dung skill.
- `domain.py`: model rieng cua feature nhu `CodeFile`, `CodeReference`.
- `ports.py`: interface noi bo feature nhu `CodeIndexPort`.
- `filesystem_indexer.py`: implementation Level 1 bang filesystem/git/text search.
- `tools.py`: tool definitions va executor cua feature.
- `hooks.py`: validate/audit hook cho tool cua feature.
- `mcp_server.py`: MCP stdio wrapper goi tool qua `ExecuteToolCallUseCase`.

## Tool naming

Tool cua feature phai co namespace:

```text
code_index.list_files
code_index.search_text
code_index.read_file
```

Khong dung ten chung chung nhu `list_files`, `search_text`, `read_file` trong harness-level registry, vi sau nay se co nhieu plugin/skill co tool trung y nghia.

## Hook rule

Moi execution cua code index tool phai di qua lifecycle:

```text
ToolCall
  -> HookPoint.BEFORE_TOOL
  -> CodeIndexToolExecutor
  -> HookPoint.AFTER_TOOL
```

`BEFORE_TOOL` bat buoc validate:

- tool name thuoc namespace `code_index.*`
- arguments dung kieu
- path khong thoat workspace root
- line range hop le
- max_results hop le

MCP server, CLI, runtime, hoac future plugin loader khong duoc goi thang `FilesystemCodeIndexer` khi dang thuc thi tool cho agent. Goi thang chi duoc chap nhan trong unit test cua indexer hoac read-only service noi bo khong dai dien cho agent tool call.

## Core change rule

Neu mot level code index moi can sua `core`, phai viet ADR/doc truoc khi code, tra loi:

- Tai sao generic `Tool*` / `Hook*` hien co khong du?
- Thay doi nay co dung cho moi feature/skill hay chi rieng code index?
- Co cach dua logic vao `features/code_index` ma khong sua core khong?

Mac dinh: logic rieng cua code index nam trong feature, khong nam trong core.

## Level mapping

- Level 1: feature tool read-only, filesystem/git/text search.
- Level 2-4: van la feature, them symbol/import/signature model trong `features/code_index`.
- Level 5-7: neu can engine ngoai nhu LSP, SCIP, CodeQL thi engine la adapter cua feature hoac plugin dependency, khong thanh core domain.

## Anti-patterns

- Them `CodeIndexPort` vao `core/ports`.
- Them `CodeFile` vao `core/domain`.
- MCP server xu ly business logic rieng va khong chay hook.
- Tool name khong namespace.
- De local LLM parse code thay indexer.
- Bo qua hook validation vi tool "chi read-only".
