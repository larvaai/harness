# Applying The Harness Folder To This Project

Doc nay mo ta cach ap dung root folder `harness/` vao project hien tai va cach no nen quan he voi `src/harness`.

Ket luan ngan:

```text
harness/      = SDLC discipline bundle, plugin/rule/hook source of truth
src/harness/  = Python runtime package, agent orchestration implementation
```

Khong tron hai folder nay.

## Muc tieu cua root `harness/`

Root `harness/` nen duoc ap dung nhu bo ky luat SDLC file-based:

```text
rules      -> doc contract va workflow routing
plugins    -> skill contracts va workflow skills
hooks      -> gate/session/trace enforcement
data       -> stage policy, ownership, skill chains
schemas    -> verification/review artifacts
install    -> explicit install vao .claude/.git hooks
state      -> runtime trace/session/telemetry
```

Nhung root `harness/` khong nen tro thanh Python runtime cua app.

## Muc tieu cua `src/harness`

`src/harness` nen la package dieu phoi:

```text
LLM runtime
agent task lifecycle
skill loading
tool execution
hook/event/checkpoint
feature/plugin integration
```

No khong nen la noi moi tinh nang duoc dua vao core. Tinh nang rieng phai thanh feature/skill.

## Cach ap dung root `harness/` vao project nay

### 1. Treat as source bundle, not app package

Giu root `harness/` nhu source-of-truth cua SDLC harness. Khong import truc tiep vao `src/harness`.

Ly do:

- root `harness/` co scripts/hooks/plugins phuc vu Claude/SDLC workflow;
- `src/harness` la package Python co cung ten import `harness`;
- neu tron import path, Python co the lay nham root `harness` thay vi `src/harness`.

Rule thuc thi:

```bash
PYTHONPATH=src python -m harness.entrypoints.local_llm_workflow_cli
PYTHONPATH=src python -m harness.entrypoints.code_index_mcp_server
```

Khong tao `harness/__init__.py` tai root.

### 2. Learn patterns, reimplement boundaries

Ap dung concept tu root `harness/` vao `src/harness` bang boundaries rieng:

| Root harness concept | Ap dung vao `src/harness` |
| --- | --- |
| `plugins/*/skills/*/SKILL.md` | `features/<name>/skill.yaml` + `instructions.md` |
| `hooks/*.py` co class telemetry/nudge/compliance | `HookRunnerPort` + feature hooks + future hook policy |
| `rules/*.md` | docs trong `docs/harness/` va docs feature |
| `data/stage-policy.yaml` | future approval/run policy |
| `schemas/*` | future artifact schemas cho verification/review |
| `state/trace` JSONL | future event/checkpoint adapters |

Khong copy nguyen plugin/hook root vao `src/harness` neu chua co use case ro.

### 3. Installation stays explicit

Root `harness/install/` chi nen chay khi user yeu cau setup SDLC harness vao repo/tooling. Dev-loop binh thuong cua Python runtime khong tu dong mutate `.claude/`.

### 4. Documentation stays in docs

Khi nghien cuu/ap dung root harness, viet ket qua vao:

```text
docs/harness/
docs/<feature>/
plans/<slug>/
```

Khong them docs project moi vao root `harness/` tru khi dang maintain SDLC bundle.

## Kien truc muc tieu

```text
User / MCP client / CLI
  -> entrypoints/
  -> runtime/
  -> core/use_cases/
  -> core/ports/
  -> adapters/ or features/
  -> core/domain result
```

Feature/plugin flow:

```text
features/<name>/skill.yaml
  -> runtime skill loader
  -> tool definitions + hooks
  -> RunTaskUseCase tools
  -> ExecuteToolCallUseCase
```

Root harness workflow influence:

```text
harness/rules/primary-workflow.md
  -> understand
  -> implement
  -> verify
  -> review/explain
```

Trong project Python, flow nay nen anh xa thanh:

```text
docs/plan first for broad/risky work
core use case for stable orchestration
feature tools/hooks for capabilities
tests for verification
events/checkpoints for trace
```

## Mapping hien tai

### Root `harness/`

Hien co:

```text
harness/README.md
harness/manifest.json
harness/hooks/
harness/plugins/
harness/rules/
harness/data/
harness/schemas/
harness/install/
harness/state/
```

Dung cho:

- source of truth SDLC rules;
- always-load contract va on-demand workflow docs;
- plugin skill contracts nhu `hs:plan`, `hs:cook`, `hs:test`;
- hook posture: telemetry, nudge, compliance;
- stage/gate/trace discipline.

Khong dung cho:

- Python package imports cua app;
- code index runtime implementation;
- local LLM workflow implementation;
- core domain/port.

### Core

Hien co:

```text
src/harness/core/domain/
src/harness/core/ports/
src/harness/core/services/
src/harness/core/use_cases/
```

Dung cho:

- run state;
- messages;
- LLM response abstraction;
- tool call/result;
- hook context/result;
- lifecycle events/checkpoints;
- local workflow schema.

Can giu core generic. Khong them:

- `CodeFile`, `CodeSymbol`, `CodeIndexPort`;
- LM Studio config;
- MCP message schema;
- prompt file path;
- filesystem path policy rieng cua code index.

### Adapters

Hien co:

```text
adapters/llm/lm_studio.py
adapters/context/workspace_context_retriever.py
adapters/events/in_memory_event_publisher.py
adapters/checkpoint/in_memory_checkpoint_store.py
adapters/hooks/noop_hook_runner.py
adapters/tools/rejecting_tool_executor.py
adapters/logging/llm_text_log.py
```

Dung cho:

- noi core voi LM Studio;
- context retrieval implementation;
- event/checkpoint/logging implementation;
- fake/noop/rejecting implementations de bootstrap.

Ghi chu: `WorkspaceContextRetriever` hien dang nhan optional code index object. Day la cau noi tam chap nhan duoc vi context retriever la adapter, khong phai core. Khi co skill loader, nen de runtime/feature registration noi dependency ro hon.

### Features

Hien co:

```text
features/local_llm/prompts/
features/code_index/
```

`local_llm` hien moi co prompt set cho staged workflow. No nen tien hoa thanh feature day du:

```text
features/local_llm/
  skill.yaml
  instructions.md
  prompts/
  policy.yaml
```

`code_index` da la feature tot hon:

```text
features/code_index/
  skill.yaml
  instructions.md
  domain.py
  ports.py
  filesystem_indexer.py
  tools.py
  hooks.py
  mcp_server.py
```

Chuan cho future feature:

```text
features/<feature_name>/
  skill.yaml
  instructions.md
  tools.py
  hooks.py
  domain.py       # optional
  ports.py        # optional
  policy.yaml     # optional
```

### Runtime

Hien co:

```text
runtime/lm_studio.py
runtime/local_llm.py
```

Dung cho:

- tao LLM adapter;
- tao lifecycle manager;
- tao event/checkpoint/hook adapters;
- noi use case voi adapters;
- load prompts cua local workflow;
- noi code index vao context retriever.

Can nang cap:

- them generic `runtime/bootstrap.py`;
- them `runtime/container.py`;
- them skill loader/register tool/register hook;
- bot hard-code tung feature trong runtime.

### Entrypoints

Hien co:

```text
entrypoints/lm_studio_cli.py
entrypoints/local_llm_workflow_cli.py
entrypoints/code_index_mcp_server.py
```

Dung cho:

- parse args;
- goi runtime builder;
- in JSON/text result;
- expose MCP stdio server.

Entrypoint khong nen:

- tu tao tool result;
- tu validate feature policy;
- tu parse code;
- bypass `ExecuteToolCallUseCase`.

## Cach them mot feature moi

Thu tu:

1. Doc `harness/rules/primary-workflow.md` neu day la change lon.
2. Doc `docs/harness/development_rules.md`.
3. Viet `docs/<feature>/architecture_rules.md` neu feature co ranh gioi rieng.
4. Tao `src/harness/features/<feature_name>/skill.yaml`.
5. Tao `instructions.md`.
6. Neu co tool, tao `tools.py` voi namespaced tool names.
7. Neu co validation/audit, tao `hooks.py`.
8. Neu can model rieng, tao `domain.py` trong feature.
9. Neu can interface rieng, tao `ports.py` trong feature.
10. Tao tests feature.
11. Chi sua runtime de register feature.
12. Chi sua core neu rule moi dung chung cho moi feature.

## Cach them mot adapter moi

Thu tu:

1. Tim core port co san.
2. Neu chua co port, chung minh port do generic.
3. Implement adapter trong `src/harness/adapters/<kind>/`.
4. Test adapter rieng voi fake provider/file/db khi co the.
5. Sua runtime de chon adapter.

Vi du:

```text
LLMPort -> adapters/llm/ollama.py
CheckpointStorePort -> adapters/checkpoint/sqlite_checkpoint_store.py
EventPublisherPort -> adapters/events/jsonl_event_publisher.py
```

## Cach them MCP server moi

MCP server nen nam gan feature neu expose tool cua feature.

Dung:

```text
features/code_index/mcp_server.py
entrypoints/code_index_mcp_server.py
```

Sai:

```text
adapters/code_index/mcp_server.py  # neu chua ro la adapter dung chung
core/mcp_server.py
```

MCP server phai:

- expose `tools/list` tu `ToolDefinition`;
- map `tools/call` thanh `ToolCall`;
- goi `ExecuteToolCallUseCase`;
- tra `structuredContent` tu `ToolResult.metadata`;
- khong goi thang tool handler khi day la agent tool execution.

## Cach dung root harness skills nhu reference

Root `harness/plugins/hs/README.md` liet ke SDLC skills:

```text
hs:plan
hs:cook
hs:test
hs:code-review
hs:ship
hs:scout
hs:debug
hs:fix
```

Khi xay runtime Python:

- dung cac skill nay nhu workflow reference;
- khong import/copy skill content vao core;
- neu can behavior tu skill, tao feature/plugin native trong `src/harness/features`;
- neu can orchestrator, doc `harness/rules/orchestrator-skills.md` va giu chain-by-name.

## Hook posture mapping

Root `harness/rules/harness-contract.md` chia hook thanh:

```text
telemetry  -> fail-open
nudge      -> advisory
compliance -> blocking fail-closed
```

Trong `src/harness`, hien moi co `HookPoint` va `HookRunnerPort`. Khi them hook policy, nen map posture nay thanh metadata/policy generic, khong hard-code vao tung feature.

Vi du tuong lai:

```text
HookResult.metadata["class"] = "compliance"
ApprovalPolicy / HookPolicy quyet dinh fail-open hay fail-closed
```

## Cach ap dung cho local LLM workflow

Local LLM yeu can workflow chia nho:

```text
normalize
decompose
retrieve context
extract facts
plan
final write
```

Trong project hien tai, workflow nay dang nam trong `RunLocalLLMWorkflowUseCase`. Giai doan tiep theo nen:

- giu schema validation trong core neu schema la generic cho workflow nay;
- dua prompt/config vao `features/local_llm`;
- de context retrieval su dung feature tools qua registry khi co registry;
- de runtime load `local_llm` nhu mot skill thay vi hard-code prompt set.

## Ranh gioi quan trong

`core` co the biet:

```text
ToolDefinition
ToolCall
ToolResult
HookPoint
HookContext
HookResult
LLMPort
ToolExecutorPort
ContextRetrieverPort
```

`core` khong biet:

```text
code_index.read_file
FilesystemCodeIndexer
LM Studio base URL
MCP initialize/tools/list schema
tree-sitter
CodeQL
prompt markdown file path
```

## Ket luan

Ap dung root `harness/` va `src/harness` vao project nay theo huong:

```text
Root harness la SDLC source bundle.
Python harness la runtime package.
Core Python nho va on dinh.
Feature/plugin phong phu nhung co bien gioi.
Runtime noi day dependency.
Entrypoint mong.
Tool nao cung qua hook lifecycle.
```
