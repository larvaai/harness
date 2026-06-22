# Harness Development Rules

Doc nay ghi cac luat de tranh pha kien truc khi phat trien quanh hai folder:

```text
harness/      root SDLC harness bundle
src/harness/  Python agent runtime package
```

## 1. Bat dau tu business flow

Truoc khi tao file/folder moi, viet duoc cau:

```text
Actor nao goi?
Use case nao dang chay?
Du lieu nao vao/ra?
Buoc nay thuoc core, adapter, feature, runtime hay entrypoint?
```

Neu chua tra loi duoc, dung code va viet docs/plan truoc.

## 1.1. Phan biet root harness va Python harness

Root `harness/`:

- la source bundle cho SDLC rules/hooks/plugins;
- co `manifest.json`, `hooks/`, `plugins/`, `rules/`, `data/`, `install/`;
- duoc install/copy vao `.claude/` chi khi goi installer tuong minh;
- khong phai Python package cua app.

`src/harness/`:

- la Python package runtime cua project;
- chua core/use cases/adapters/features/runtime/entrypoints;
- la noi code Python product dang duoc build.

Luat:

- Khong import module tu root `harness/` vao `src/harness`.
- Khong tao `harness/__init__.py` o root.
- Khong them root `harness/` vao package discovery.
- Python commands phai uu tien `PYTHONPATH=src`.
- Neu muon ap dung concept tu root `harness/`, viet adapter/feature rieng trong `src/harness`, khong copy logic nguyen khối.

## 2. Core la nho nhat co the

Duoc dua vao `core` khi logic:

- dung cho moi agent/skill/tool;
- song lau va on dinh;
- khong phu thuoc provider, filesystem, subprocess, MCP, HTTP, database;
- co the test bang fake/in-memory adapters.

Khong dua vao `core`:

- code index model;
- LM Studio details;
- MCP protocol details;
- prompt noi dung;
- tool rieng cua feature;
- parser/static analyzer rieng;
- path policy rieng cua mot tool.

## 3. Feature/skill la goi nang luc

Moi nang luc agent nen nam trong:

```text
src/harness/features/<feature_name>/
  skill.yaml
  instructions.md
  domain.py
  ports.py
  tools.py
  hooks.py
  policy.yaml        # optional
```

Feature co the co domain/port rieng. Domain/port rieng cua feature khong tu dong tro thanh core domain/port.

Root `harness/plugins/*/skills/*/SKILL.md` la reference ve skill contract. Khi xay feature trong `src/harness/features`, hoc pattern ve manifest/instructions/gates, nhung van giu format runtime Python rieng (`skill.yaml`, `instructions.md`, `tools.py`, `hooks.py`).

Vi du dung:

```text
src/harness/features/code_index/domain.py
src/harness/features/code_index/ports.py
```

Vi du sai:

```text
src/harness/core/domain/code_index.py
src/harness/core/ports/code_index.py
```

## 4. Tool execution phai qua lifecycle

Agent tool call khong duoc goi thang tool handler.

Bat buoc:

```text
ToolCall
  -> ExecuteToolCallUseCase
  -> LifecycleManager.reach(BEFORE_TOOL)
  -> ToolExecutorPort.execute
  -> RuntimeState.apply_tool_result
  -> LifecycleManager.reach(AFTER_TOOL)
```

Neu expose tool qua MCP, CLI, API, worker hay plugin loader, wrapper do van phai goi qua `ExecuteToolCallUseCase`.

## 5. Hook la noi validate/cross-cutting checks

Hook nen dung cho:

- validate path/arguments;
- audit tool result;
- enforce workspace boundary;
- collect trace metadata;
- block unsafe action.

Hook khong nen chua business logic chinh cua tool.

## 6. Adapter chi noi voi the gioi ngoai

Adapter duoc phep biet:

- HTTP provider;
- filesystem implementation;
- MCP/stdin/stdout protocol;
- database;
- shell/subprocess;
- third-party SDK.

Adapter khong duoc tu quyet dinh business policy neu policy do nen dung chung cho moi adapter.

## 7. Runtime chi noi day dependency

Runtime duoc lam:

- khoi tao adapter;
- load feature/skill;
- register tool/hook;
- tao use case da du dependency;
- doc config.

Runtime khong duoc lam:

- parse LLM response truc tiep;
- chay tool bypass lifecycle;
- chua prompt business logic;
- chua validation rieng cua feature.

## 8. Entrypoint mong

Entrypoint chi nen:

- parse CLI args / request;
- goi runtime builder;
- in/return result;
- map error ra exit code/protocol response.

Neu entrypoint co nhieu logic, day logic xuong runtime, feature, adapter hoac core use case tuy theo ranh gioi.

## 9. Naming rules

Tool cua feature phai namespace:

```text
<feature_name>.<action>
```

Vi du:

```text
code_index.list_files
code_index.search_text
code_index.read_file
```

Khong dung ten chung chung trong registry tong quat:

```text
read_file
search_text
list_files
```

Ngoai le chi chap nhan trong test fake hoac docs vi du.

## 9.1. Markdown va docs

Theo root `harness/rules/documentation-management.md`, markdown moi cua project nen nam trong `docs/` hoac `plans/`. Root `harness/` co san nhieu markdown vi no la imported SDLC bundle; khong tao docs project moi trong root `harness/`.

Dung:

```text
docs/harness/
docs/local_llm/
plans/<slug>/
```

Khong dung:

```text
harness/new-project-note.md
harness/plugins/.../README.md   # tru khi dang maintain plugin bundle that su
```

## 10. Khi nao can sua docs

Phai sua docs truoc hoac cung PR khi:

- them feature/skill moi;
- them hook point moi;
- them core port/use case moi;
- them MCP server moi;
- thay doi tool lifecycle;
- thay doi folder boundary;
- nang code index len level moi.

## 11. Checklist truoc khi merge

- Khong co feature-specific model trong `core`.
- Moi tool execution di qua hook lifecycle.
- Tool co namespace.
- Runtime chi noi day dependency.
- Entrypoint khong chua business logic.
- Root `harness/` khong bi tron voi `src/harness`.
- Test core dung fake/in-memory.
- Test feature cover tool executor va hook validation.
- Docs cua feature duoc cap nhat.
