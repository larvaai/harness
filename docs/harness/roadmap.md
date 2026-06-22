# Harness Roadmap

Roadmap nay giup ap dung root `harness/` vao project va nang `src/harness` thanh runtime plugin/skill ro rang ma khong lam vo ranh gioi hien co.

## Phase 0: Docs va guardrails

Trang thai: dang thuc hien.

Done khi:

- Co `docs/harness/`.
- Co rule doc truoc khi code.
- Co docs rieng cho feature co rui ro kien truc nhu `code_index`.
- Code index khong nam trong core.
- Phan biet ro root `harness/` va Python package `src/harness`.

## Phase 0.5: Root harness intake

Muc tieu: ghi nhan root `harness/` la SDLC source bundle va quyet dinh cach dung trong repo nay.

Can lam:

```text
Doc root harness layout
Doc import/name-collision risk
Quyet dinh khi nao chay harness/install/install.py
Quyet dinh file nao cua root harness duoc maintain trong project nay
```

Done khi:

- Khong co command/test nao import nham root `harness/`.
- Project commands dung `PYTHONPATH=src`.
- Root `harness/` khong bi copy vao `src/harness`.
- Docs noi ro root harness la reference/source bundle, khong phai app package.

## Phase 1: Tool registry

Muc tieu: runtime co the register tools tu nhieu feature.

Can them:

```text
core/ports/tool_registry.py        # neu can generic port
core/services/tool_input_validator.py
adapters/tools/in_memory_tool_registry.py
runtime/tool_registry_bootstrap.py
```

Can can nhac:

- Tool registry la generic, co the vao core/service/port.
- Tool implementation cua feature van o `features/<name>/tools.py`.
- Tool name bat buoc namespace.

Done khi:

- `RunTaskUseCase` nhan tool definitions tu registry.
- `ExecuteToolCallUseCase` dispatch tool qua executor/registry.
- Tests cover unknown tool, invalid args, safe tool.

## Phase 2: Composite hook runner

Muc tieu: nhieu feature co hook cung chay trong mot lifecycle.

Can them:

```text
adapters/hooks/composite_hook_runner.py
```

Hoac neu hook routing la rule generic:

```text
core/services/hook_router.py
```

Done khi:

- `NoopHookRunner`, `CodeIndexToolHookRunner`, future hooks co the chay cung nhau.
- Hook failure policy ro rang.
- Test thu tu hook va block behavior.

Nen hoc tu root `harness/rules/harness-contract.md`:

- telemetry fail-open;
- nudge advisory;
- compliance blocking fail-closed.

Nhung posture policy phai thanh generic policy trong Python runtime, khong copy raw root hook code.

## Phase 3: Skill loader

Muc tieu: runtime load feature/skill tu `skill.yaml`.

Can them:

```text
core/domain/skill.py               # chi model generic
core/ports/skill_loader.py
adapters/skills/filesystem_skill_loader.py
runtime/skill_bootstrap.py
```

Khong lam:

- Khong dua model rieng cua code index vao `core/domain/skill.py`.
- Khong hard-code prompt path trong use case.

Done khi:

- Load duoc `features/code_index/skill.yaml`.
- Load duoc `features/local_llm` sau khi feature nay co manifest.
- Runtime register tools/hooks dua tren skill metadata.

Reference:

- root `harness/plugins/hs/README.md`
- root `harness/rules/orchestrator-skills.md`

Ap dung nguyen tac chain-by-name, khong import logic cua skill khac vao orchestrator.

## Phase 4: Approval policy

Muc tieu: tool medium/dangerous khong the bypass approval.

Can them:

```text
core/domain/approval.py
core/ports/approval.py
core/services/approval_policy.py
adapters/approval/cli_approval.py
```

Done khi:

- `DangerLevel.SAFE` auto allow.
- `DangerLevel.MEDIUM` phai qua policy.
- `DangerLevel.DANGEROUS` can explicit approval.
- Tool rejection khong lam hong state.

## Phase 5: Persistent event/checkpoint/memory

Muc tieu: run co the inspect/resume.

Can them:

```text
adapters/events/jsonl_event_publisher.py
adapters/checkpoint/file_checkpoint_store.py
adapters/checkpoint/sqlite_checkpoint_store.py
core/ports/memory.py
```

Done khi:

- Moi run co event log doc duoc.
- Checkpoint persist qua process restart.
- Resume run co doc state moi nhat.

## Phase 6: Unify local LLM workflow as skill

Muc tieu: local LLM staged workflow khong la runtime hard-code.

Can lam:

```text
features/local_llm/skill.yaml
features/local_llm/instructions.md
features/local_llm/policy.yaml
runtime load prompts qua skill loader
```

Done khi:

- Runtime khong hard-code prompt file list.
- Local workflow co manifest.
- Context retrieval co the su dung registered feature tools.

## Phase 7: Feature/plugin expansion

Moi feature moi phai theo pattern:

```text
features/<name>/
  skill.yaml
  instructions.md
  tools.py
  hooks.py
```

Ung vien:

- `code_index` Level 2 symbols/imports/signatures.
- `workspace_edit` edit/apply patch tools.
- `test_runner` test/lint/typecheck tools.
- `memory` persistent project memory.
- `reviewer` code review workflow.

Rule:

- Feature/plugin duoc them ma khong bat core sua, tru khi can generic abstraction moi.
