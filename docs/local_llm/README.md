# Local LLM Harness Implementation Roadmap

## 1. Bai toan

Local LLM thuong gap cac gioi han:

```text
Khong du thong minh nhu model lon.
Context ngan.
De quen.
De lech instruction.
De sinh output sai schema.
De tu tin voi suy luan khong co source.
```

Vi vay harness khong nen giao cho local LLM "nghi toan bo". Harness phai bien local LLM thanh mot cong nhan xu ly task nho, con harness giu vai tro:

```text
manager
memory
policy
validator
reviewer
controller
checkpoint store
tool verifier
approval gate
```

Cong thuc thiet ke:

```text
Model = generator
Harness = controller
Tools = source of truth
Tests = judge
Human = approval for risky actions
```

## 2. Nguyen tac cot loi

Voi ChatGPT/Claude manh, co the dua mot yeu cau lon:

```text
Hay doc project, hieu kien truc, tim bug, sua code, viet test, giai thich.
```

Voi local LLM yeu, khong lam vay. Phai tach thanh:

```text
1. Hieu task
2. Chuan hoa yeu cau
3. Chon file lien quan
4. Doc tung phan nho
5. Trich xuat facts
6. Tao plan nho
7. Validate plan
8. Execute tung buoc
9. Kiem tra output
10. Review doc lap
11. Tong hop ket qua
```

Local LLM chi nen xu ly tung buoc nho, voi input ngan, output schema ro.

Khong bao gio cho local LLM vua doc nhieu context, vua lap ke hoach, vua sua code, vua tu danh gia trong mot lan goi.

## 3. Workflow tong the

Workflow muc cao:

```text
User Request
   v
Request Normalizer
   v
Task Decomposer
   v
Context Retriever
   v
Micro Task Runner
   v
Output Validator
   v
Reviewer
   v
Executor / Tool Caller
   v
Verifier
   v
Final Synthesizer
```

Workflow chi tiet:

```text
User gui yeu cau
   v
[1] Chuan hoa yeu cau
   v
[2] Phan ra thanh task nho
   v
[3] Xac dinh context can doc
   v
[4] Trich xuat facts tu context
   v
[5] Tao plan dua tren facts
   v
[6] Validate plan
   v
[7] Thuc thi tung action nho
   v
[8] Kiem tra ket qua bang rule/tool/test
   v
[9] Review boi agent khac hoac prompt khac
   v
[10] Xuat cau tra loi cuoi
```

Workflow implement day du:

```text
User Request
  output: raw user request
  v
Normalize Request
  output: TaskSpec
  v
Decompose Task
  output: TaskGraph
  v
Retrieve Context
  output: ContextPack
  v
Extract Facts
  output: FactSet
  v
Build Plan
  output: Plan
  v
Validate Plan
  output: rule-based decision
  v
Execute Step
  output: Patch/Action
  v
Validate Output
  output: schema + policy decision
  v
Review Patch
  output: LLM reviewer verdict
  v
Run Tool Verifier
  output: tests/lint/typecheck result
  v
Repair Loop
  output: repair task if failed
  v
Final Report
```

## 4. Role architecture cho local LLM yeu

Nen chia thanh nhieu vai tro logic, du co the dung cung mot local model:

```text
Normalizer Agent
Decomposer Agent
Context Selector Agent
Fact Extractor Agent
Planner Agent
Executor Agent
Reviewer Agent
Verifier Agent
Final Writer Agent
```

Khong bat buoc dung nhieu model. Co the la cung mot model, khac prompt:

```text
Same Local LLM
  - prompt_normalizer
  - prompt_decomposer
  - prompt_fact_extractor
  - prompt_planner
  - prompt_reviewer
  - prompt_final_writer
```

Harness dieu phoi. Model khong tu dieu phoi.

## 5. State machine bat buoc

Run lifecycle nen la state machine, khong de LLM tu nhay buoc:

```text
CREATED
  v
NORMALIZED
  v
DECOMPOSED
  v
CONTEXT_COLLECTED
  v
FACTS_EXTRACTED
  v
PLANNED
  v
PLAN_VALIDATED
  v
EXECUTING
  v
OUTPUT_VALIDATED
  v
REVIEWED
  v
VERIFIED
  v
COMPLETED
```

State loi:

```text
NORMALIZATION_FAILED
DECOMPOSITION_FAILED
CONTEXT_INSUFFICIENT
PLAN_REJECTED
PATCH_INVALID
REVIEW_FAILED
TEST_FAILED
NEEDS_HUMAN_APPROVAL
```

Ly do:

```text
Local LLM yeu de troi.
State machine giup harness biet dang o buoc nao.
Moi buoc co input/output ro.
Moi state loi co repair/escalation path rieng.
```

## 6. Checkpoint o moi buoc

Vi local LLM context ngan, moi buoc phai luu checkpoint. Khong dua vao conversation context.

Checkpoint vi du:

```json
{
  "run_id": "run_123",
  "state": "FACTS_EXTRACTED",
  "task_spec": "...",
  "task_graph": "...",
  "context_pack_ids": ["ctx_1", "ctx_2"],
  "fact_set": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

External state co the luu bang:

```text
SQLite
Postgres
JSONL
local file
```

Moi lan goi model, harness build prompt lai tu checkpoint can thiet.

## 7. Lop memory/context

Can 5 lop memory/context:

### Lop 1: Run State

Luu trang thai hien tai cua task:

```text
task_spec
task_graph
current_step
completed_steps
failed_steps
```

### Lop 2: Fact Store

Luu facts da trich xuat:

```text
F1, F2, F3...
```

Facts ngan hon code rat nhieu.

### Lop 3: Code Index

Luu cau truc code:

```text
file tree
symbols
imports
class/function signatures
call graph
```

### Lop 4: Artifact Store

Luu patch, logs, test result:

```text
patch_1.diff
pytest_result_1.txt
review_1.json
```

### Lop 5: Summary Store

Luu summary ngan sau moi buoc:

```text
T1 completed: found memory files...
T2 completed: SQLiteMemoryAdapter uses JSON serialization...
```

Moi prompt chi lay:

```text
task_spec
current_step
relevant facts
relevant context chunks
output schema
```

Khong lay toan bo lich su.

## 8. Step 1: Request Normalizer

Muc tieu: bien yeu cau tu nhien cua user thanh task ro rang.

Input vi du:

```text
User: Hay sua phan memory cua agent cho on dinh hon.
```

Output bat buoc theo schema:

```json
{
  "goal": "Improve stability of agent memory system",
  "task_type": "code_modification",
  "success_criteria": [
    "Memory can save runtime state",
    "Memory can restore previous run",
    "Errors are handled safely",
    "Existing tests pass"
  ],
  "constraints": [
    "Do not rewrite unrelated modules",
    "Preserve hexagonal architecture"
  ],
  "unknowns": [
    "Current memory implementation is not inspected yet"
  ]
}
```

Rule:

```text
Bat local LLM dien form.
Khong cho tra loi van xuoi tu do.
Unknowns phai duoc giu lai de context retriever xu ly sau.
```

## 9. Step 2: Task Decomposer

Tu normalized request, chia thanh micro-task.

Output vi du:

```json
{
  "tasks": [
    {
      "id": "T1",
      "name": "Locate memory-related files",
      "type": "read_only",
      "expected_output": "List of candidate files"
    },
    {
      "id": "T2",
      "name": "Summarize current memory design",
      "type": "analysis",
      "depends_on": ["T1"],
      "expected_output": "Facts about current implementation"
    },
    {
      "id": "T3",
      "name": "Identify stability gaps",
      "type": "analysis",
      "depends_on": ["T2"],
      "expected_output": "List of issues"
    },
    {
      "id": "T4",
      "name": "Propose minimal patch plan",
      "type": "planning",
      "depends_on": ["T3"],
      "expected_output": "Patch plan"
    },
    {
      "id": "T5",
      "name": "Apply patch",
      "type": "code_edit",
      "depends_on": ["T4"],
      "expected_output": "Modified files"
    },
    {
      "id": "T6",
      "name": "Run tests",
      "type": "verification",
      "depends_on": ["T5"],
      "expected_output": "Test result"
    }
  ]
}
```

Harness kiem tra:

```text
Co task qua lon khong?
Co task thieu expected_output khong?
Co task sua code truoc khi doc code khong?
Co task khong co dependency hop ly khong?
```

Neu sai, bat LLM lam lai.

## 10. Step 3: Context Retriever

Local LLM context ngan thi khong nhet full repo.

Dung co che lay context ngoai model:

```text
Code index
Keyword search
AST parser
Call graph
File map
Symbol table
Vector DB neu can
Knowledge graph neu co
```

Quy trinh vi du:

```text
Task: "Find memory implementation"
   v
Harness search:
   - file names: memory, checkpoint, state, store
   - symbols: MemoryPort, save, load, RuntimeState
   - imports related to memory
   v
Return top small chunks
```

Context dua vao model nen nho:

```text
File path
Class/function signatures
30-80 dong lien quan
Summary cu neu co
```

Khong dua ca file 1000 dong neu chi can 80 dong.

## 11. Step 4: Fact Extraction bat buoc

Truoc khi bat local LLM lap ke hoach, bat no trich xuat fact.

Khong hoi:

```text
Hay hieu doan code nay.
```

Hoi:

```text
Extract only verifiable facts from the provided code.
Do not infer beyond the text.
Return JSON.
```

Output:

```json
{
  "facts": [
    {
      "id": "F1",
      "claim": "MemoryPort defines save(state) and load(run_id)",
      "source": "core/ports/memory.py",
      "confidence": "high"
    },
    {
      "id": "F2",
      "claim": "SQLiteMemoryAdapter serializes RuntimeState as JSON",
      "source": "adapters/memory/sqlite_memory.py",
      "confidence": "high"
    },
    {
      "id": "F3",
      "claim": "There is no explicit transaction handling in save()",
      "source": "adapters/memory/sqlite_memory.py",
      "confidence": "medium"
    }
  ],
  "unknowns": [
    "No test file for SQLiteMemoryAdapter was found in provided context"
  ]
}
```

Rule:

```text
Khong cho local LLM suy luan troi.
Moi fact phai co source.
Unknown phai duoc ghi rieng.
Confidence chi duoc la high, medium, low.
```

## 12. Step 5: Planner dua tren facts

Planner input gom:

```text
Normalized request
Micro tasks
Extracted facts
Constraints
```

Planner khong duoc nhin full repo.

Output vi du:

```json
{
  "plan": [
    {
      "step": 1,
      "action": "Add error handling around SQLite save transaction",
      "reason": "F3 indicates save() lacks explicit transaction handling",
      "files": ["adapters/memory/sqlite_memory.py"],
      "risk": "medium"
    },
    {
      "step": 2,
      "action": "Add tests for save/load roundtrip",
      "reason": "Unknown test coverage for memory adapter",
      "files": ["tests/adapters/memory/test_sqlite_memory.py"],
      "risk": "low"
    }
  ],
  "requires_approval": true
}
```

Harness validate:

```text
Moi action co reason tu fact khong?
Co sua file ngoai pham vi khong?
Co test khong?
Co buoc nguy hiem khong?
```

Neu khong dat, reject plan.

## 13. Step 6: Executor chi lam mot action nho

Khong dua prompt:

```text
Hay sua memory system.
```

Dua prompt:

```text
Apply only this change:
- In adapters/memory/sqlite_memory.py
- Wrap save() operation in transaction
- Preserve public interface
- Do not modify unrelated files

Return unified diff only.
```

Output bat buoc co the la unified diff:

```diff
--- a/adapters/memory/sqlite_memory.py
+++ b/adapters/memory/sqlite_memory.py
@@ ...
```

Hoac JSON structured patch:

```json
{
  "file": "adapters/memory/sqlite_memory.py",
  "operation": "replace_function",
  "symbol": "SQLiteMemoryAdapter.save",
  "new_code": "..."
}
```

Voi local LLM yeu, tot nhat khong cho no edit truc tiep toan file.

Nen dung mot trong hai cach:

```text
Cach A: LLM tao unified diff, harness apply diff.
Cach B: LLM tao structured patch, harness apply bang AST/tool.
```

Cach B an toan hon.

## 14. Step 7: Validator kiem output truoc khi chay

Moi output cua LLM phai qua validator.

Validator cho JSON:

```text
Co parse duoc JSON khong?
Co du field khong?
Field co dung enum khong?
File path co nam trong workspace khong?
```

Validator cho diff:

```text
Diff co apply duoc khong?
Co sua file ngoai plan khong?
Co xoa nhieu dong bat thuong khong?
Co them import nguy hiem khong?
```

Validator cho shell command:

```text
Command co nam trong allowlist khong?
Co chua rm -rf, curl | sh, sudo khong?
Co can approval khong?
```

Nguyen tac:

```text
Khong tin output cua local LLM.
Moi output phai machine-checkable.
```

## 15. Step 8: Reviewer doc lap

Sau khi Executor tao patch, goi Reviewer bang prompt khac.

Reviewer khong duoc biet "dap an mong muon". No chi nhan:

```text
Original task
Plan
Patch
Relevant code context
```

Reviewer output neu can sua:

```json
{
  "verdict": "needs_changes",
  "issues": [
    {
      "severity": "high",
      "message": "Patch changes MemoryPort interface but plan required preserving public interface",
      "evidence": "Diff modifies core/ports/memory.py"
    }
  ],
  "required_fixes": [
    "Revert MemoryPort change",
    "Keep changes inside SQLiteMemoryAdapter"
  ]
}
```

Reviewer output neu dat:

```json
{
  "verdict": "approved",
  "issues": []
}
```

Ly do:

```text
Model yeu sinh output de sai.
Chia vai "nguoi lam" va "nguoi kiem" tang do chinh xac.
```

## 16. Step 9: Verifier bang tool that

Khong hoi LLM:

```text
Code nay dung chua?
```

Dung tool:

```text
ruff / eslint / mypy
pytest / vitest
type checker
unit tests
import check
build check
snapshot test
```

Workflow:

```text
Patch generated
   v
Apply patch
   v
Run formatter
   v
Run linter
   v
Run type check
   v
Run tests
   v
If fail:
      summarize error
      create repair task
   else:
      approve
```

Neu test fail, khong dua toan bo log dai vao local LLM. Rut gon:

```text
command
exit code
first error
relevant stack trace
related file
last 30 lines
```

LLM chi giai thich ket qua tool, khong thay the tool.

## 17. Step 10: Final Synthesizer

Chi den cuoi moi cho LLM viet bao cao.

Input:

```text
Original request
Completed tasks
Files changed
Tests run
Remaining issues
```

Output:

```text
Da lam:
- ...
File thay doi:
- ...
Kiem tra:
- ...
Con lai:
- ...
```

Final Writer khong duoc tu bia them viec chua lam.

Harness nen cap facts:

```json
{
  "completed": ["T1", "T2", "T3", "T4", "T5", "T6"],
  "changed_files": [
    "adapters/memory/sqlite_memory.py",
    "tests/adapters/memory/test_sqlite_memory.py"
  ],
  "commands_run": [
    {
      "cmd": "pytest tests/adapters/memory",
      "exit_code": 0
    }
  ],
  "remaining_issues": []
}
```

## 18. Prompt pattern cho local LLM yeu

### Pattern 1: Role nho

Khong dung:

```text
You are a senior software architect...
```

Dung:

```text
You are a strict JSON extraction worker.
Your only job is to extract facts from the provided code.
Do not propose solutions.
Do not modify code.
```

### Pattern 2: Output schema cung

Luon co:

```text
Return valid JSON only.
No markdown.
No explanation outside JSON.
```

### Pattern 3: Negative instruction ro

```text
Do not infer missing information.
Do not invent files.
Do not modify unrelated modules.
Do not change public interfaces unless explicitly requested.
```

### Pattern 4: Self-check ngan

Cuoi prompt them:

```text
Before finalizing, check:
- Is the output valid JSON?
- Are all claims supported by provided context?
- Did you avoid unsupported assumptions?
```

Khong yeu cau chain-of-thought. Chi yeu cau ket qua da kiem.

## 19. Prompt mau: Fact Extractor

```text
You are a strict fact extraction worker.

Task:
Extract verifiable facts from the provided code context.

Rules:
- Only use the provided context.
- Do not infer beyond the text.
- Do not propose solutions.
- Do not modify code.
- Every fact must include a source file.
- If something is unclear, put it in unknowns.

Return valid JSON only.

JSON schema:
{
  "facts": [
    {
      "id": "F1",
      "claim": "string",
      "source": "string",
      "confidence": "high | medium | low"
    }
  ],
  "unknowns": ["string"]
}

Context:
{{context}}
```

## 20. Prompt mau: Planner

```text
You are a cautious planning worker.

Task:
Create a minimal implementation plan using only the provided facts.

Rules:
- Every plan step must cite at least one fact id.
- Do not modify files not mentioned in the context unless necessary.
- Prefer minimal changes.
- Preserve public interfaces unless the task explicitly requires changing them.
- Include verification steps.

Return valid JSON only.

JSON schema:
{
  "plan": [
    {
      "step": 1,
      "action": "string",
      "reason_fact_ids": ["F1"],
      "target_files": ["string"],
      "risk": "low | medium | high"
    }
  ],
  "requires_approval": true
}

TaskSpec:
{{task_spec}}

Facts:
{{facts}}
```

## 21. Prompt mau: Executor

```text
You are a patch generation worker.

Task:
Generate a patch for exactly one approved plan step.

Rules:
- Only modify target files.
- Do not change public interfaces unless explicitly allowed.
- Do not include explanations.
- Return unified diff only.
- If the change cannot be made with the provided context, return:
  CANNOT_PATCH: <reason>

Approved plan step:
{{plan_step}}

Relevant code:
{{context}}
```

## 22. Prompt mau: Reviewer

```text
You are a strict code review worker.

Task:
Review whether the patch follows the approved plan.

Rules:
- Check for unrelated changes.
- Check for public interface changes.
- Check for missing error handling.
- Check whether verification is needed.
- Do not rewrite the patch.
- Return valid JSON only.

JSON schema:
{
  "verdict": "approved | needs_changes | rejected",
  "issues": [
    {
      "severity": "low | medium | high",
      "message": "string",
      "evidence": "string"
    }
  ],
  "required_fixes": ["string"]
}

Original task:
{{task_spec}}

Approved plan:
{{plan}}

Patch:
{{patch}}
```

## 23. Quyen quyet dinh cuoi nam o harness

Local LLM khong duoc giu quyen quyet dinh cuoi.

Workflow quyen luc:

```text
LLM de xuat
Harness validate
LLM sua
Harness kiem
Tool xac minh
Reviewer danh gia
Human approval neu nguy hiem
```

Tuc la:

```text
Model = generator
Harness = controller
Tools = source of truth
Tests = judge
Human = approval for risky actions
```

## 24. ContextPack design

Moi lan goi LLM, harness tao mot `ContextPack`.

```json
{
  "context_pack_id": "ctx_001",
  "purpose": "plan memory stability patch",
  "token_budget": 2500,
  "items": [
    {
      "type": "task_spec",
      "content": "..."
    },
    {
      "type": "fact_set",
      "content": "..."
    },
    {
      "type": "code_chunk",
      "file": "adapters/memory/sqlite_memory.py",
      "start_line": 10,
      "end_line": 90,
      "content": "..."
    }
  ]
}
```

Quy tac:

```text
ContextPack phai co muc dich cu the.
Khong co context thua.
Co token budget.
Co source path.
Co line range neu la code.
```

## 25. Chat luong output va scoring

Moi output nen duoc cham diem tu dong.

Vi du:

```json
{
  "schema_valid": true,
  "source_grounded": true,
  "within_scope": true,
  "risk_level": "low",
  "requires_retry": false
}
```

Neu khong dat:

```text
Retry voi prompt sua loi
hoac chuyen sang human review
hoac thu them context
```

## 26. Retry policy

Local LLM yeu se loi format nhieu. Can retry co kiem soat.

```text
Attempt 1:
  normal prompt

Attempt 2:
  include validation error
  ask to fix only schema

Attempt 3:
  reduce task size
  simplify output

Attempt 4:
  escalate to human or stronger model
```

Validation error vi du:

```text
Your previous output was invalid JSON because:
- Missing field: facts
- confidence value "certain" is not allowed

Return corrected JSON only.
```

Khong retry vo han.

## 27. Human approval checkpoint

Cac action sau phai yeu cau approval:

```text
sua nhieu file
xoa file
chay shell command khong nam trong allowlist
thay doi public interface
thay doi migration/database
cai package
thay doi config deploy
gui request network
```

Approval object:

```json
{
  "approval_id": "appr_123",
  "reason": "Patch modifies public interface MemoryPort",
  "risk": "high",
  "requested_action": "...",
  "affected_files": ["core/ports/memory.py"]
}
```

## 28. Map-Reduce cho codebase lon

Local LLM khong doc duoc nhieu context thi dung map-reduce.

Vi du can hieu module memory:

```text
Map phase:
  chunk 1 -> facts
  chunk 2 -> facts
  chunk 3 -> facts

Reduce phase:
  merge facts
  remove duplicates
  detect conflicts
  create module summary
```

Khong dua 20 file vao mot prompt.

Dua tung file/chunk:

```text
File A -> facts_A
File B -> facts_B
File C -> facts_C
```

Sau do:

```text
facts_A + facts_B + facts_C -> module_summary
```

Neu facts qua dai, reduce tiep.

## 29. Multi-agent harness structure de xuat

Folder core:

```text
core/
  domain/
    task_spec.py
    task_graph.py
    context_pack.py
    fact.py
    plan.py
    patch.py
    review.py
    verification.py
    checkpoint.py

  use_cases/
    run_workflow.py
    normalize_request.py
    decompose_task.py
    retrieve_context.py
    extract_facts.py
    build_plan.py
    execute_plan_step.py
    review_output.py
    verify_result.py

  ports/
    llm.py
    context_retriever.py
    code_index.py
    patch_applier.py
    command_runner.py
    checkpoint_store.py
    approval.py
    event_publisher.py
```

Adapters:

```text
adapters/
  llm/
    ollama_adapter.py
    llama_cpp_adapter.py
  context/
    ripgrep_retriever.py
    tree_sitter_index.py
    vector_retriever.py
  patch/
    unified_diff_applier.py
  command/
    subprocess_runner.py
  checkpoint/
    sqlite_checkpoint_store.py
```

Features:

```text
features/
  code_editing/
    prompts/
      normalizer.md
      decomposer.md
      fact_extractor.md
      planner.md
      executor.md
      reviewer.md
```

## 30. Business logic nam o harness, khong nam trong prompt

Prompt chi la cach hoi model.

Business logic that nam o harness:

```text
State machine
Validation rule
Retry policy
Approval policy
Context budget policy
Tool permission policy
Plan acceptance policy
Verification policy
```

Rule vi du:

```python
def validate_plan(plan: Plan, facts: FactSet) -> ValidationResult:
    for step in plan.steps:
        if not step.reason_fact_ids:
            return invalid("Every step must cite at least one fact")

        if step.risk == "high" and not plan.requires_approval:
            return invalid("High-risk plan must require approval")

    return valid()
```

Day moi la phan giup local LLM "tuan thu nhu Claude".

Khong phai vi model ngoan hon, ma vi harness khong cho no lam sai.

## 31. MVP nen build truoc

Dung build full ngay. Bat dau voi MVP:

```text
1. User request
2. Normalize request -> JSON
3. Decompose task -> JSON
4. Retrieve context bang grep/file search
5. Extract facts -> JSON
6. Plan -> JSON
7. Validate plan bang code
8. Generate patch cho mot step
9. Apply diff
10. Run test
11. Final report
```

Chua can:

```text
vector DB
multi-agent that
LangGraph phuc tap
distributed worker
UI approval xin
```

Sau khi MVP on moi them.

## 32. Lo trinh implement chi tiet

### Phase 1: Domain va state machine

Muc tieu:

```text
Co the bieu dien TaskSpec, TaskGraph, ContextPack, FactSet, Plan, Patch, Review, VerificationResult va workflow state.
```

Can build:

```text
core/domain/task_spec.py
core/domain/task_graph.py
core/domain/context_pack.py
core/domain/fact.py
core/domain/plan.py
core/domain/patch.py
core/domain/review.py
core/domain/verification.py
core/domain/local_workflow_state.py
```

Done khi:

```text
Moi output cua local LLM co domain object tuong ung.
State machine co valid transitions.
State loi duoc dinh nghia ro.
```

### Phase 2: Schema validators

Muc tieu:

```text
Moi output JSON/diff/command cua local LLM deu machine-checkable.
```

Can build:

```text
core/services/validators/task_spec_validator.py
core/services/validators/task_graph_validator.py
core/services/validators/fact_set_validator.py
core/services/validators/plan_validator.py
core/services/validators/patch_validator.py
core/services/validators/command_validator.py
```

Done khi:

```text
Invalid JSON bi reject.
Missing field bi reject.
Enum sai bi reject.
Path ngoai workspace bi reject.
Plan khong cite fact bi reject.
High-risk plan khong approval bi reject.
```

### Phase 3: Prompt workers

Muc tieu:

```text
Local LLM chi duoc goi qua worker co role nho va schema cung.
```

Can build:

```text
features/code_editing/prompts/normalizer.md
features/code_editing/prompts/decomposer.md
features/code_editing/prompts/fact_extractor.md
features/code_editing/prompts/planner.md
features/code_editing/prompts/executor.md
features/code_editing/prompts/reviewer.md
```

Done khi:

```text
Moi worker co prompt rieng.
Moi prompt co role nho.
Moi prompt co output schema.
Moi prompt co negative instructions.
Moi prompt khong yeu cau chain-of-thought.
```

### Phase 4: Context retrieval co gioi han

Muc tieu:

```text
Khong dua full repo vao local LLM.
```

Can build:

```text
core/ports/context_retriever.py
core/ports/code_index.py
adapters/context/ripgrep_retriever.py
adapters/context/file_chunker.py
adapters/context/simple_symbol_index.py
```

Done khi:

```text
Retriever tra ve file path, signature, line range, code chunk 30-80 dong.
ContextPack co purpose va token_budget.
ContextPack khong co context thua.
```

### Phase 5: Fact extraction va fact store

Muc tieu:

```text
LLM lap plan dua tren facts, khong dua tren cam giac.
```

Can build:

```text
core/use_cases/extract_facts.py
core/domain/fact.py
core/ports/fact_store.py
adapters/fact_store/in_memory_fact_store.py
```

Done khi:

```text
Moi fact co id, claim, source, confidence.
Unknowns duoc luu.
Fact co the truy xuat theo task/module/file.
```

### Phase 6: Planner va plan validation

Muc tieu:

```text
Plan nho, co source-grounded reasons, co risk, co verification step.
```

Can build:

```text
core/use_cases/build_plan.py
core/services/plan_validator.py
core/domain/plan.py
```

Done khi:

```text
Moi plan step cite fact id.
Target files nam trong scope.
High-risk step require approval.
Plan co verification.
Plan sai bi retry/reject.
```

### Phase 7: Patch execution an toan

Muc tieu:

```text
Executor chi lam mot approved plan step.
```

Can build:

```text
core/use_cases/execute_plan_step.py
core/domain/patch.py
core/ports/patch_applier.py
adapters/patch/unified_diff_applier.py
```

Done khi:

```text
Patch chi sua target files.
Diff apply duoc truoc khi ghi that.
Patch ngoai scope bi reject.
Structured patch/AST patch duoc uu tien neu co.
```

### Phase 8: Reviewer doc lap

Muc tieu:

```text
Sinh patch va review patch la hai vai rieng.
```

Can build:

```text
core/use_cases/review_output.py
core/domain/review.py
features/code_editing/prompts/reviewer.md
```

Done khi:

```text
Reviewer tra verdict approved, needs_changes hoac rejected.
Issue co severity, message, evidence.
needs_changes tao repair task.
```

### Phase 9: Tool verifier

Muc tieu:

```text
Tests/tools la judge, khong phai LLM.
```

Can build:

```text
core/use_cases/verify_result.py
core/domain/verification.py
core/ports/command_runner.py
adapters/command/subprocess_runner.py
```

Done khi:

```text
Run formatter/linter/typecheck/test theo config.
Log dai duoc summarize truoc khi dua lai cho LLM.
Fail tao repair task.
Pass cho phep final report.
```

### Phase 10: Retry, approval, repair loop

Muc tieu:

```text
Local LLM loi format/logic duoc sua co kiem soat, khong retry vo han.
```

Can build:

```text
core/services/retry_policy.py
core/services/approval_policy.py
core/use_cases/request_approval.py
core/use_cases/repair_failed_step.py
```

Done khi:

```text
Attempt 1 normal prompt.
Attempt 2 fix schema only.
Attempt 3 reduce task size.
Attempt 4 escalate human/stronger model.
Risky actions tao ApprovalRequest.
Approval denied khong lam hong state.
```

### Phase 11: Final synthesizer

Muc tieu:

```text
Final answer chi tong hop facts do harness cung cap.
```

Can build:

```text
core/use_cases/finalize_report.py
features/code_editing/prompts/final_writer.md
```

Done khi:

```text
Report gom completed tasks, changed files, commands run, remaining issues.
Final writer khong bia viec chua lam.
```

## 33. Chay thu use case voi LM Studio

LM Studio can bat OpenAI-compatible local server tai:

```text
http://localhost:1234/v1
```

Kiem tra model LM Studio dang expose:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.lm_studio_cli --list-models
```

Chay use case that qua core `RunTaskUseCase`, lifecycle hooks, events va checkpoints:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.lm_studio_cli \
  'Reply with exactly: harness-ok' \
  --model gemma-4-31b-it-qat-uncensored-heretic \
  --temperature 0 \
  --max-tokens 32 \
  --show-trace
```

Output ky vong:

```text
status: finished

final_answer:
harness-ok

trace:
- event: before_run
- event: on_state_saved
- event: before_llm_call
- event: on_state_saved
- event: after_llm_call
- event: on_state_saved
- event: after_run
- event: on_state_saved
- checkpoint[1]: run_started
- checkpoint[2]: before_llm_call
- checkpoint[3]: after_llm_response
- checkpoint[4]: run_finished
```

Chay prompt khac:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.lm_studio_cli \
  'Summarize the purpose of an agent harness in one paragraph.' \
  --model gemma-4-31b-it-qat-uncensored-heretic \
  --temperature 0.2 \
  --max-tokens 256 \
  --show-trace
```

In full `RunResult` dang JSON:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.lm_studio_cli \
  'Reply with exactly: harness-ok' \
  --model gemma-4-31b-it-qat-uncensored-heretic \
  --temperature 0 \
  --max-tokens 32 \
  --json
```

Dung base URL khac neu LM Studio khong chay o port mac dinh:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.lm_studio_cli \
  'Reply with exactly: harness-ok' \
  --base-url http://localhost:1234/v1 \
  --model gemma-4-31b-it-qat-uncensored-heretic
```

Ghi chu debug:

```text
Neu LM Studio tra "Model unloaded.", hay load model trong LM Studio hoac chon model khac tu --list-models.
Neu status failed voi loi "LLM response must include a final answer or at least one tool call", model co the dang tra content rong.
Mot so reasoning model co the dung het max_tokens vao reasoning_content, hay tang --max-tokens hoac chon instruct model khac.
```

Chay test sau khi sua adapter/runtime:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest
```

## 34. Chay workflow local_llm MVP voi model nho

Workflow MVP hien tai la read-only:

```text
Normalize request
-> Decompose task
-> Retrieve workspace context
-> Extract facts
-> Build read-only plan
-> Validate plan
-> Final report
```

Workflow nay chua apply patch va chua chay command verifier. Muc tieu la test kha nang bat model nho lam viec theo tung buoc nho voi JSON schema va validator.

Chay workflow voi LM Studio model nho:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.local_llm_workflow_cli \
  'Analyze the current hook and checkpoint lifecycle in src/harness/core. Extract grounded facts and produce a read-only plan. Do not edit files.' \
  --model qwable-9b-claude-fable-5 \
  --temperature 0 \
  --max-tokens 4096 \
  --max-context-items 4 \
  --textlog-name local_llm \
  --json
```

Output ky vong:

```text
"state": "completed"
"task_spec": {...}
"task_graph": {...}
"context_pack": {...}
"fact_set": {...}
"plan": {...}
"final_report": {...}
"error": null
```

Text log rieng de doc bang mat nguoi se duoc ghi tai:

```text
var/local_llm/llm-textlog.txt
```

File nay khac log binh thuong. No ghi day du tung step goi LLM:

```text
LLM STEP: normalizer
LLM STEP: decomposer
LLM STEP: fact_extractor
LLM STEP: planner
LLM STEP: final_writer
```

Moi step gom:

```text
Human-Readable Answer
Parsed JSON
Raw LLM Response
System Prompt Sent
User Payload Sent
```

Doc text log:

```bash
sed -n '1,260p' var/local_llm/llm-textlog.txt
```

Dung ten folder khac theo dang `var/some-name-here/llm-textlog.txt`:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.local_llm_workflow_cli \
  'Analyze the current hook and checkpoint lifecycle in src/harness/core. Extract grounded facts and produce a read-only plan. Do not edit files.' \
  --model qwable-9b-claude-fable-5 \
  --temperature 0 \
  --max-tokens 4096 \
  --max-context-items 4 \
  --textlog-name some-name-here
```

Hoac chi dinh path truc tiep:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.local_llm_workflow_cli \
  'Analyze the current hook and checkpoint lifecycle in src/harness/core. Extract grounded facts and produce a read-only plan. Do not edit files.' \
  --model qwable-9b-claude-fable-5 \
  --textlog-path var/some-name-here/llm-textlog.txt
```

Tat text log:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.local_llm_workflow_cli \
  'Analyze src/harness/core.' \
  --model qwable-9b-claude-fable-5 \
  --no-textlog
```

Chay ban ngan gon de xem summary:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.local_llm_workflow_cli \
  'Analyze the current hook and checkpoint lifecycle in src/harness/core. Extract grounded facts and produce a read-only plan. Do not edit files.' \
  --model qwable-9b-claude-fable-5 \
  --temperature 0 \
  --max-tokens 4096 \
  --max-context-items 4
```

Neu muon debug output tung worker:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m harness.entrypoints.local_llm_workflow_cli \
  'Analyze the current hook and checkpoint lifecycle in src/harness/core. Extract grounded facts and produce a read-only plan. Do not edit files.' \
  --model qwable-9b-claude-fable-5 \
  --temperature 0 \
  --max-tokens 4096 \
  --max-context-items 4 \
  --show-raw
```

Ghi chu khi dung model nho:

```text
Neu fact extraction fail vi JSON bi cat ngang, tang --max-tokens hoac giam --max-context-items.
Neu retriever lay sai context, them path cu the vao task, vi du src/harness/core.
Neu model reasoning tra content rong, chon model instruct khac hoac tang --max-tokens.
```

## 35. Cong thuc quan trong

Voi local LLM yeu:

```text
Accuracy = Small Task + Good Context + Strict Schema + External Validation + Retry + Tool Verification
```

Khong phai:

```text
Accuracy = Bigger Prompt + More Instructions
```

Prompt dai khong cuu duoc model yeu. Workflow tot moi cuu duoc.

## 36. Ket luan thiet ke

Workflow nen dung:

```text
User Request
-> Normalize
-> Decompose
-> Retrieve Context
-> Extract Facts
-> Plan
-> Validate Plan
-> Execute One Small Step
-> Validate Output
-> Review
-> Verify by Tools
-> Checkpoint
-> Repeat
-> Final Report
```

Local LLM chi lam:

```text
phan loai
trich xuat
tom tat
lap plan nho
sinh patch nho
review theo checklist
```

Harness lam:

```text
giu state
gioi han context
validate schema
kiem policy
goi tool
chay test
retry
checkpoint
approval
```

Neu thiet ke dung, local LLM khong can "thong minh nhu Claude". No chi can du tot cho tung micro-task. Do chinh xac den tu he thong kiem soat xung quanh no, khong den tu model don le.
