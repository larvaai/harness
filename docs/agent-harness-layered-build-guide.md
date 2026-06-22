# Agent Harness Layered Build Guide

## 1. Cach hieu project

Project nay khong nen duoc thiet ke nhu "mot con agent" don le. Nen xem no la mot runtime dieu phoi agent, skill, tool, hook, memory, approval va tracing theo mot tap luat thong nhat.

Mot request cua user co the di qua vong doi:

```text
Task -> Prompt -> LLM -> Tool Call -> Hook -> Event -> Memory -> Result
```

Kien truc phai sinh ra tu vong doi nay, khong bat dau bang viec ve folder `core`, `adapter`, `port` truoc.

Muc tieu cua docs nay la dinh nghia thu tu build theo tang truoc khi implementation:

```text
Business flow -> Domain -> Use case -> Port -> Adapter -> Runtime -> Feature -> Observability -> Memory -> Approval
```

## 2. Nguyen tac thiet ke

Core chi chua luat nghiep vu on dinh cua harness.

Adapter chi la cach noi core voi the gioi ben ngoai: LLM provider, database, shell, CLI, API, tracing backend.

Feature va skill la goi nang luc mo rong: prompt, tool, hook, config, policy rieng.

Runtime la noi noi day dependency, khong phai noi chua business logic.

Entrypoint la noi user buoc vao he thong: CLI, API, worker, UI.

Neu doi OpenAI sang Ollama, SQLite sang Postgres, CLI sang Web API ma business flow phai sua nhieu, nghia la core dang bi tron voi infrastructure.

## 3. Use case nen dinh nghia truoc

Truoc khi code, can viet ro cac use case bang ngon ngu nghiep vu.

### Use Case 1: Run User Task

User gui mot task. System tao run, chon agent hoac skill phu hop, build prompt, goi LLM, xu ly tool call neu co, ghi trace, cap nhat state va tra ket qua cuoi.

### Use Case 2: Execute Tool Call

Agent yeu cau goi tool. System kiem tra tool ton tai, validate input, check approval, chay hook truoc tool, execute tool, chay hook sau tool, ghi event va tra result ve agent.

### Use Case 3: Load Skill

System nhan task, tim skill phu hop, load prompt, tools, hooks va config cua skill, sau do gan skill vao runtime.

### Use Case 4: Human Approval

Agent muon thuc hien hanh dong co rui ro nhu sua file, chay command, cai package hoac xoa du lieu. System tao approval request, dung execution, cho policy hoac user quyet dinh, roi tiep tuc hoac tu choi.

### Use Case 5: Persist And Resume Run

Sau moi buoc quan trong, system luu state, messages, tool results, artifacts va events. Khi can, run co the resume tu checkpoint.

## 4. Tang 1: Domain Model

Tang nay dinh nghia cac khai niem nghiep vu song lau trong system.

Nen co cac object toi thieu:

```text
Task
Agent
Skill
Prompt
Message
ToolDefinition
ToolCall
ToolResult
Hook
HookContext
Event
RuntimeState
ApprovalRequest
ApprovalDecision
MemoryRecord
RunResult
```

Quy tac:

```text
Domain khong import OpenAI, Anthropic, LangGraph, FastAPI, SQLite, subprocess.
Domain khong biet tool duoc chay bang Python function, shell hay MCP.
Domain chi mo ta su vat va trang thai trong the gioi harness.
```

Output cua tang nay:

```text
src/harness/core/domain/
```

Dieu kien hoan thanh:

```text
Co du object de mo ta mot run.
Co the tao RuntimeState tu Task.
Co the append assistant response va tool result vao state.
Co the tao RunResult tu state.
```

## 5. Tang 2: Core Use Cases

Tang nay chua orchestration nghiep vu. Day la trai tim cua harness.

Use case quan trong nhat la `RunTaskUseCase`.

Workflow toi thieu:

```text
Create run
Load skill / agent config
Build prompt
Call LLM
If final answer: finish
If tool calls: execute tool calls
Append results to state
Save state
Loop until finished
Return result
```

`ExecuteToolCallUseCase` nen xu ly rieng:

```text
Find tool
Validate input
Check danger level
Request approval if needed
Run before_tool hooks
Execute tool
Run after_tool hooks
Publish events
Return ToolResult
```

Output cua tang nay:

```text
src/harness/core/use_cases/run_task.py
src/harness/core/use_cases/execute_tool_call.py
src/harness/core/use_cases/load_skill.py
src/harness/core/use_cases/resume_run.py
```

Dieu kien hoan thanh:

```text
Business flow chay duoc voi fake adapters.
Use case khong import provider that.
Tool policy khong nam trong tool handler.
Hook flow co thu tu ro rang.
```

## 6. Tang 3: Ports

Port la interface ma core can de noi ra ben ngoai.

Port phai duoc suy ra tu workflow, khong suy ra tu folder structure.

Danh sach port toi thieu:

```text
LLMPort
PromptBuilderPort hoac PromptBuilder service
ToolRegistryPort
ToolExecutorPort
ApprovalPort
EventPublisherPort
HookRunnerPort
MemoryPort
SkillLoaderPort
ClockPort
IdGeneratorPort
```

Vi du:

```python
class LLMPort(Protocol):
    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        ...


class ToolExecutorPort(Protocol):
    def execute(self, call: ToolCall) -> ToolResult:
        ...


class MemoryPort(Protocol):
    def load(self, run_id: str) -> RuntimeState | None:
        ...

    def save(self, state: RuntimeState) -> None:
        ...
```

Output cua tang nay:

```text
src/harness/core/ports/
```

Dieu kien hoan thanh:

```text
Moi lan core can goi ra ngoai deu thong qua port.
Co fake/in-memory implementation de test core.
Port dat ten theo nhu cau nghiep vu, khong dat ten theo provider.
```

## 7. Tang 4: Core Services And Policies

Tang nay chua cac rule nghiep vu khong phai entity va khong phai adapter.

Nen co:

```text
PromptBuilder
ToolCallPolicy
RunPolicy
SkillResolver
ApprovalPolicy
StateTransitionPolicy
ToolInputValidator
```

Vi du rule thuoc core:

```text
Tool phai duoc dang ky truoc.
Tool input phai validate theo schema.
Tool nguy hiem phai qua approval.
Moi tool call phai co event.
Hook phai chay dung thu tu.
Tool loi khong mac dinh lam chet runtime neu policy cho phep recover.
```

Output cua tang nay:

```text
src/harness/core/services/
```

Dieu kien hoan thanh:

```text
Rule bat bien khong nam trong adapter.
Tool handler chi lam hanh dong, khong tu quyet dinh policy.
Prompt khong hard-code trong RunTaskUseCase.
```

## 8. Tang 5: Adapters

Adapter implement cac port bang cong nghe cu the.

Vi du:

```text
LLMPort
  - OpenAIAdapter
  - AnthropicAdapter
  - OllamaAdapter
  - FakeLLMAdapter

MemoryPort
  - SQLiteMemoryAdapter
  - FileMemoryAdapter
  - InMemoryMemoryAdapter

EventPublisherPort
  - ConsoleEventPublisher
  - JSONLEventPublisher
  - OpenTelemetryEventPublisher

ApprovalPort
  - CLIApprovalAdapter
  - AutoApprovalAdapter
  - WebApprovalAdapter

ToolExecutorPort
  - PythonFunctionToolExecutor
  - ShellToolExecutor
  - MCPToolExecutor
```

Output cua tang nay:

```text
src/harness/adapters/
```

Dieu kien hoan thanh:

```text
Adapter map du lieu provider ve domain object cua core.
Adapter co the thay the ma khong sua use case.
Loi provider duoc doi thanh loi co nghia trong harness.
```

## 9. Tang 6: Runtime Bootstrap

Runtime la noi doc config va noi day dependency.

Runtime nen lam:

```text
Load config
Khoi tao adapters
Load features / skills
Register tools
Register hooks
Inject dependencies vao use cases
Tao App object cho entrypoint su dung
```

Runtime khong nen lam:

```text
Khong dieu khien chi tiet run lifecycle.
Khong chua tool policy.
Khong hard-code prompt nghiep vu.
Khong xu ly provider response truc tiep trong use case.
```

Output cua tang nay:

```text
src/harness/runtime/bootstrap.py
src/harness/runtime/config.py
src/harness/runtime/container.py
src/harness/runtime/app.py
```

Dieu kien hoan thanh:

```text
CLI/API chi can goi App hoac use case da duoc bootstrap.
Co the doi adapter bang config.
Feature loader duoc goi tai bootstrap, khong nam trong core use case.
```

## 10. Tang 7: Features And Skills

Feature la goi nang luc nghiep vu. Skill khong thay the runtime; skill chi khai bao va mo rong hanh vi.

Moi skill co the gom:

```text
skill.yaml
instructions.md
tools.py
hooks.py
policy.yaml
```

Vi du:

```text
src/harness/features/coding_assistant/
  skill.yaml
  instructions.md
  tools.py
  hooks.py
```

`skill.yaml` nen mo ta:

```yaml
name: coding_assistant
description: Read, edit, test, and explain code
tools:
  - read_file
  - list_files
  - edit_file
  - run_tests
hooks:
  before_tool:
    - validate_workspace_path
  after_tool:
    - log_tool_result
```

Quy tac:

```text
Prompt nam trong skill, khong nam trong core.
Tool metadata nam canh tool.
Hook cua skill chi mo rong, khong giau business logic song con.
Them skill moi khong bat core phai sua.
```

### Code index feature guardrail

`code_index` la mot feature/skill/tool cua agent, khong phai core. Truoc khi sua code index, phai doc:

```text
docs/local_llm/code_index/architecture_rules.md
docs/local_llm/code_index/implementation_plan.md
```

Quy tac rieng:

```text
Khong them CodeIndex* vao core/domain hoac core/ports.
Code index tool phai nam trong src/harness/features/code_index/.
Tool name phai co namespace code_index.*.
MCP server khong duoc bypass ExecuteToolCallUseCase va hooks.
Moi code index tool execution phai qua BEFORE_TOOL va AFTER_TOOL.
```

Output cua tang nay:

```text
src/harness/features/
```

Dieu kien hoan thanh:

```text
Co the load it nhat mot skill tu folder.
Skill dang ky duoc prompt, tool, hook.
RunTaskUseCase co the chay voi skill da load.
```

## 11. Tang 8: Events And Tracing

Event la lich su co cau truc cua run.

Event toi thieu:

```text
run_started
skill_loaded
prompt_built
llm_requested
llm_responded
tool_requested
tool_approved
tool_rejected
tool_started
tool_succeeded
tool_failed
state_saved
run_finished
run_failed
```

Ban dau nen luu JSONL:

```json
{"type":"run_started","run_id":"run_123"}
{"type":"tool_requested","run_id":"run_123","tool":"read_file"}
{"type":"tool_succeeded","run_id":"run_123","tool":"read_file"}
```

Output cua tang nay:

```text
src/harness/core/domain/event.py
src/harness/core/ports/event_publisher.py
src/harness/adapters/events/jsonl_event_publisher.py
```

Dieu kien hoan thanh:

```text
Moi buoc quan trong co event.
Event khong phu thuoc UI.
Trace co the doc lai de debug run.
```

## 12. Tang 9: Memory And Checkpoint

Memory ban dau nen don gian, uu tien resume run hon la "tri nho thong minh".

Nen luu:

```text
run_id
task
messages
tool_calls
tool_results
status
artifacts
created_at
updated_at
```

Adapter dau tien nen la SQLite hoac file JSON.

Output cua tang nay:

```text
src/harness/core/ports/memory.py
src/harness/adapters/memory/sqlite_memory.py
```

Dieu kien hoan thanh:

```text
Run co the save sau moi loop.
Run co the load lai bang run_id.
State duoc version hoa neu schema co kha nang thay doi.
```

## 13. Tang 10: Approval And Sandbox

Tool can co danger level.

Phan loai ban dau:

```text
safe:
  - read_file
  - list_files

medium:
  - edit_file
  - run_tests

dangerous:
  - run_shell_command
  - delete_file
  - install_package
```

Policy ban dau:

```text
safe -> auto allow
medium -> allow neu trong workspace va dung policy
dangerous -> can explicit approval
```

Output cua tang nay:

```text
src/harness/core/services/approval_policy.py
src/harness/core/ports/approval.py
src/harness/adapters/approval/cli_approval.py
```

Dieu kien hoan thanh:

```text
Tool nguy hiem khong the bypass approval.
Approval request co du context de user quyet dinh.
Tu choi approval khong lam hong state.
```

## 14. Folder Structure De Xuat

MVP nen bat dau gon:

```text
src/harness/
  core/
    domain.py
    ports.py
    run_task.py
  adapters/
    llm_fake.py
    llm_openai.py
    tool_executor.py
    event_jsonl.py
  features/
    coding/
      skill.yaml
      instructions.md
      tools.py
  runtime/
    bootstrap.py
    config.py
  cli.py
tests/
pyproject.toml
```

Khi logic lon hon, tach thanh:

```text
src/harness/
  core/
    domain/
    ports/
    services/
    use_cases/
  adapters/
    llm/
    tools/
    memory/
    events/
    approval/
  features/
  runtime/
  entrypoints/
tests/
```

Khong nen tao folder qua lon khi chua co logic chay that.

## 15. Thu Tu Implementation

### Phase 1: Single Agent Run

Muc tieu:

```text
User input -> LLM -> final answer
```

Can co:

```text
Task
Message
RuntimeState
LLMPort
FakeLLMAdapter
RunTaskUseCase
CLI entrypoint
```

Done khi:

```text
CLI nhan input va tra final answer.
Core test chay bang FakeLLMAdapter.
```

### Phase 2: Tool Call

Muc tieu:

```text
User input -> LLM -> tool call -> tool result -> LLM -> final answer
```

Them:

```text
ToolDefinition
ToolCall
ToolResult
ToolRegistryPort
ToolExecutorPort
read_file
list_files
```

Done khi:

```text
LLM fake co the yeu cau read_file.
Tool result duoc append vao state.
Run loop tiep tuc den final answer.
```

### Phase 3: Event Trace

Muc tieu:

```text
Moi buoc quan trong deu co event.
```

Them:

```text
Event
EventPublisherPort
JSONLEventPublisher
```

Done khi:

```text
Co file trace JSONL doc duoc theo run_id.
```

### Phase 4: Hooks

Muc tieu:

```text
Co extension point truoc/sau cac buoc lon.
```

Them:

```text
before_run
after_run
before_llm_call
after_llm_call
before_tool
after_tool
on_error
```

Done khi:

```text
Hook co the block mot tool call hoac them metadata vao event.
```

### Phase 5: Skill System

Muc tieu:

```text
Dong goi prompt + tools + hooks thanh feature.
```

Them:

```text
Skill
SkillLoaderPort
FileSkillLoader
PromptBuilder
```

Done khi:

```text
Co it nhat mot skill load tu folder va chay duoc.
```

### Phase 6: Memory And Resume

Muc tieu:

```text
Run co checkpoint va co the resume.
```

Them:

```text
MemoryPort
FileMemoryAdapter hoac SQLiteMemoryAdapter
resume_run use case
```

Done khi:

```text
Dung giua run van co the load lai state.
```

### Phase 7: Approval And Sandbox

Muc tieu:

```text
Tool co rui ro phai duoc kiem soat.
```

Them:

```text
danger_level
ApprovalPolicy
ApprovalPort
workspace path validation
```

Done khi:

```text
edit_file va run_command khong the chay neu policy/approval tu choi.
```

### Phase 8: Multi-Agent Orchestration

Chi lam sau khi single-agent harness da on.

Muc tieu:

```text
Task co the duoc chia cho nhieu agent/skill.
```

Them:

```text
AgentRegistry
Planner
ExecutionPlan
Subtask
Coordinator
```

Done khi:

```text
Coordinator co the chon skill/agent phu hop va tong hop ket qua.
```

## 16. Checklist Ra Quyet Dinh Khi Code

Khi khong biet mot logic nen dat o dau, hoi:

```text
Neu doi LLM provider, code nay co phai sua khong?
Neu doi CLI sang API, code nay co phai sua khong?
Neu doi SQLite sang Postgres, code nay co phai sua khong?
Neu them skill moi, core co phai sua khong?
Neu dung fake adapter, business flow co chay duoc khong?
Logic nay la rule bat bien hay chi la cach noi voi cong nghe?
```

Dinh huong:

```text
Sua khi doi provider -> adapter.
Sua khi doi entrypoint -> entrypoint/runtime.
Rule bat bien cua harness -> core service/use case.
Khai bao nang luc moi -> feature/skill.
Noi dependency -> runtime.
```

## 17. Anti-Patterns Can Tranh

```text
Hard-code prompt trong core use case.
De OpenAI response object chay xuyen vao domain.
De tool handler tu quyet dinh approval policy.
De hook chua logic song con cua runtime.
De runtime dieu khien tung buoc run lifecycle.
Tao folder hexagonal qua lon truoc khi co MVP chay.
Viet adapter truoc khi dinh nghia use case.
Dung memory nhu black box truoc khi co checkpoint don gian.
Them multi-agent truoc khi single-agent loop on dinh.
```

## 18. Definition Of Ready Truoc Khi Vao Code

Chi nen bat dau implementation khi cac cau hoi nay da co cau tra loi:

```text
MVP run lifecycle la gi?
Use case dau tien la gi?
Domain object toi thieu gom nhung gi?
Core can nhung port nao?
Fake adapter nao can co de test core?
Tool dau tien la tool nao?
Event toi thieu can ghi la gi?
Skill dau tien ten gi va gom prompt/tool/hook nao?
Policy approval ban dau ra sao?
MVP se chay qua CLI hay API?
```

De xuat cau tra loi ban dau:

```text
MVP run lifecycle: Task -> Fake/OpenAI LLM -> final answer.
Use case dau tien: RunTaskUseCase.
Domain toi thieu: Task, Message, RuntimeState, RunResult.
Port dau tien: LLMPort, EventPublisherPort.
Fake adapter: FakeLLMAdapter, InMemoryEventPublisher.
Tool dau tien: read_file, list_files.
Event dau tien: run_started, llm_requested, llm_responded, run_finished.
Skill dau tien: coding_assistant.
Approval ban dau: safe auto allow, dangerous deny/ask.
Entrypoint dau tien: CLI.
```

## 19. Ket Luan

Huong build dung cho project nay la:

```text
Dung run lifecycle lam xuong song.
Dung domain de dat ten the gioi nghiep vu.
Dung use case de giu business flow.
Dung port de core khong phu thuoc cong nghe.
Dung adapter de thay provider/infrastructure.
Dung runtime de noi day.
Dung feature/skill de mo rong nang luc.
Dung event/memory/approval de kiem soat va resume.
```

Khi implementation, moi tang chi nen duoc them vao vi co mot nhu cau trong workflow that. Nhu vay project se lon len tu business logic thay vi lon len tu folder structure.
