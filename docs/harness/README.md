# Harness Docs

Project nay hien co hai thu cung ten "harness":

```text
harness/      SDLC harness file-based: rules, hooks, plugins, skills, state, installer
src/harness/  Python agent runtime package dang duoc xay trong project nay
```

Doc nay giai thich cach ap dung root folder `harness/` vao project ma khong pha ranh gioi cua Python package `src/harness`.

Doc nay la diem vao bat buoc truoc khi sua kien truc harness.

## Doc truoc khi code

Neu thay doi lien quan den `src/harness`, doc theo thu tu:

1. `docs/harness/README.md`
2. `docs/harness/development_rules.md`
3. `docs/harness/apply_harness_folder.md`
4. `docs/agent-harness-layered-build-guide.md`

Neu thay doi mot feature cu the, doc them docs cua feature do. Vi du:

- `docs/local_llm/code_index/architecture_rules.md`
- `docs/local_llm/code_index/implementation_plan.md`

## Mental model: hai lop harness

### Root `harness/`

Root `harness/` la source-of-truth SDLC bundle. No gom:

```text
hooks/      gate/session/trace hooks
plugins/    hs:* skills va plugin siblings
rules/      always-load va on-demand rules
data/       policies, ownership, stage policy, skill chains
schemas/    artifact schemas
install/    installer vao .claude/.git hooks khi goi tuong minh
state/      runtime trace/session/telemetry
```

Theo `harness/README.md`, dev-loop khong tu dong dung `.claude/`; installer chi copy khi duoc goi tuong minh. Root `harness/` nen duoc xem nhu vendor/source bundle cho SDLC discipline.

### `src/harness/`

`src/harness` la Python runtime package cua project nay. No dieu phoi agent:

Harness dieu phoi vong doi:

```text
Task
  -> Prompt / Skill
  -> LLM
  -> ToolCall
  -> BEFORE_TOOL hooks
  -> ToolExecutor
  -> AFTER_TOOL hooks
  -> Events / Checkpoints
  -> Result
```

Python core chi biet cac khai niem chung:

```text
Task, Message, LLMResponse
ToolDefinition, ToolCall, ToolResult
HookPoint, HookContext, HookResult
RuntimeState, Checkpoint, RunResult
```

Python feature/skill moi la noi biet nang luc rieng:

```text
code_index
local_llm workflow prompts
future coding tools
future memory tools
future browser or shell tools
```

## Folder map hien tai cua `src/harness`

```text
src/harness/
  core/         stable domain, ports, services, use cases
  adapters/    implementation noi core voi ngoai he thong
  features/    skill/tool/prompt/hook/policy theo tung nang luc
  runtime/     bootstrap dependency va tao app/use case da noi day
  entrypoints/ CLI/MCP/process entrypoints
```

## Trang thai hien tai

Trong `src/harness` dang co:

- `RunTaskUseCase`: vong lap task -> LLM -> tool -> result.
- `ExecuteToolCallUseCase`: moi tool call di qua `BEFORE_TOOL` va `AFTER_TOOL`.
- `LifecycleManager`: publish event, run hook, save checkpoint.
- `local_llm` workflow: pipeline rieng cho local model yeu, chia task thanh buoc nho.
- `code_index` feature: skill/tool read-only Level 1 va MCP server.

Con thieu hoac con tam thoi:

- Chua co generic skill loader.
- Chua co tool registry tong quat.
- Chua co approval policy that su.
- Chua co persistent checkpoint/memory adapter ngoai in-memory.
- Runtime con hard-code mot so adapter va feature.
- `local_llm` workflow chua duoc hop nhat voi skill/plugin loader.

## Nguyen tac dung folder harness

- Root `harness/` la rule/plugin/hook source bundle; khong import vao Python core.
- `src/harness` la package runtime; khong copy nguyen plugins/hooks root vao day.
- Project docs viet trong `docs/`, khong sua markdown trong root `harness/` tru khi dang maintain SDLC bundle.
- Do trung ten `harness`, Python commands phai dung `PYTHONPATH=src` de import `src/harness`.
- Them use case chung cho moi agent vao `core/use_cases`.
- Them rule chung, song lau vao `core/services`.
- Them provider/infrastructure vao `adapters`.
- Them nang luc agent rieng vao `features`.
- Them wiring vao `runtime`.
- Them CLI/MCP/API vao `entrypoints`.
- Khong dua model rieng cua feature vao `core`.

## Cac docs lien quan

- `docs/harness/development_rules.md`: luat bat buoc khi sua code.
- `docs/harness/apply_harness_folder.md`: cach ap dung folder vao project hien tai.
- `docs/harness/roadmap.md`: thu tu nang cap de harness tro thanh plugin/skill runtime dung nghia.
- `docs/agent-harness-layered-build-guide.md`: build guide goc theo tang.
- `harness/README.md`: source-of-truth cua root SDLC harness bundle.
- `harness/rules/harness-contract.md`: contract always-load cua root harness.
