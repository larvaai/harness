# Code Index Implementation Plan

## Muc tieu

Xay dung mot Code Index Layer nam giua repo va local LLM, de harness khong dua full codebase vao prompt ma truy van du lieu co cau truc.

Quan trong: code index la mot feature/skill/tool cua agent, khong phai core. Truoc khi implement, doc `docs/local_llm/code_index/architecture_rules.md`.

```text
Repo source code
  -> Code Indexer
  -> Structured Code Map
  -> Context Retriever / Agent query tools
  -> Local LLM nhan context nho, dung cho
```

Project hien tai la Python package theo huong `core / ports / adapters / entrypoints`. Vi vay giai doan dau nen dung `git ls-files`, `pathlib`, `ripgrep` va Python `ast`; chi nang len Tree-sitter, LSP, SCIP/LSIF hoac CodeQL khi can do chinh xac cao hon.

## Nguyen tac thiet ke

- Indexer la source of truth ve cau truc code, khong phai LLM.
- LLM chi nhan context da loc: file, symbol, signature, import, usage hoac chunk lien quan.
- Moi muc index phai co model du lieu ro rang, test rieng, va co cach degrade ve text search neu parser that bai.
- Bat dau bang read-only index. Khong sua code trong qua trinh index.
- Uu tien adapter cuc bo khong phu thuoc service ngoai trong MVP.

## Kien truc de xuat

```text
src/harness/features/code_index/domain.py
src/harness/features/code_index/ports.py
src/harness/features/code_index/filesystem_indexer.py
src/harness/features/code_index/tools.py
src/harness/features/code_index/hooks.py
src/harness/features/code_index/mcp_server.py
src/harness/features/code_index/skill.yaml
src/harness/features/code_index/instructions.md
tests/code_index/
```

Luon ket noi vao `WorkspaceContextRetriever` theo cach tang dan:

```text
TaskSpec + TaskGraph
  -> code_index tools / query service
  -> candidate files / symbols / signatures / references
  -> ContextPack
```

## Data model MVP

```python
CodeFile:
    path: str
    language: str
    size_bytes: int
    line_count: int
    sha256: str

CodeSymbol:
    name: str
    kind: str
    file: str
    start_line: int
    end_line: int
    signature: str | None
    parent: str | None

CodeImport:
    file: str
    module: str
    name: str | None
    alias: str | None
    line: int

CodeReference:
    name: str
    file: str
    line: int
    column: int | None
    context: str
```

## Bang muc do

| Thu can index | Tool phu hop | Do kho | Huong lam cho repo nay |
| --- | --- | --- | --- |
| File tree | `os.walk`, `git ls-files`, `fd`, `ripgrep` | De | Dung `git ls-files` neu co git, fallback `Path.rglob` |
| Symbols | Tree-sitter, ctags, LSP | Trung binh | MVP dung Python `ast`, sau do them Tree-sitter neu multi-language |
| Imports | Tree-sitter, AST parser, language parser | Trung binh | Dung Python `ast.Import` va `ast.ImportFrom` |
| Class/function signatures | Tree-sitter, LSP, ctags | Trung binh | Dung Python `ast` + lay source line bang `end_lineno` |
| Call graph | LSP, static analyzer, CodeQL, custom AST analysis | Kho | MVP call graph noi bo theo AST, chap nhan approximate |
| References / usages | LSP, SCIP/LSIF, Sourcegraph-style index | Kho | MVP dung symbol table + ripgrep word-boundary; nang cap LSP sau |
| Data flow / security flow | CodeQL, Semgrep Pro-style analysis, custom static analysis | Rat kho | Khong dua vao MVP; them CodeQL/Semgrep khi co rule cu the |

## Cap 1 - De: File tree va text search

Muc tieu: agent biet repo co file nao va doc dung chunk lien quan ma khong can doan.

Steps:

1. Tao `CodeFile` feature object trong `src/harness/features/code_index/domain.py`.
2. Tao `CodeIndexPort` trong `src/harness/features/code_index/ports.py` voi cac method read-only:
   - `list_files() -> list[CodeFile]`
   - `search_text(query: str) -> list[CodeReference]`
   - `read_file(path: str, start_line: int | None, end_line: int | None) -> str`
3. Implement `FilesystemCodeIndexer` trong `src/harness/features/code_index/filesystem_indexer.py`.
4. Thu tu lay file:
   - uu tien `git ls-files`
   - fallback sang `Path.rglob("*")`
   - bo qua `.git`, `.pytest_cache`, `__pycache__`, `.venv`, binary files, file sinh ra trong `var/`
5. Them `RipgrepSearch` neu may co `rg`; fallback Python text scan.
6. Them tool executor trong `src/harness/features/code_index/tools.py` voi namespaced tools:
   - `code_index.list_files`
   - `code_index.search_text`
   - `code_index.read_file`
7. Them hook validation trong `src/harness/features/code_index/hooks.py`.
8. MCP server phai goi tool qua `ExecuteToolCallUseCase`, khong goi thang indexer.
9. Cap nhat `WorkspaceContextRetriever` de co the nhan optional `code_index`.
10. Viet test:
   - list file bo qua cache/binary
   - search keyword tra ve path + line
   - context retriever van fallback duoc khi khong co index

Done khi:

- ContextPack co the chua `file_tree` va `code_chunk` tu index.
- Test hien co cua `WorkspaceContextRetriever` van pass.
- Query dang "Find MemoryPort save behavior" tra ve file chua symbol lien quan.

## Cap 2 - Trung binh: Symbols

Muc tieu: agent hoi "class/function nao lien quan X?" bang index thay vi search text thuan.

Steps:

1. Them `CodeSymbol` domain object.
2. Tao `PythonAstIndexer` dung `ast.parse`.
3. Extract:
   - `ClassDef` thanh symbol kind `class`
   - `FunctionDef` / `AsyncFunctionDef` thanh `function` hoac `method`
   - constant module-level neu can, vi du bien uppercase
4. Ghi `parent` cho method nam trong class.
5. Ghi `start_line` va `end_line` tu `lineno` / `end_lineno`.
6. Them query service:
   - `find_symbols(query: str, kind: str | None = None)`
   - `get_symbol(name: str, file: str | None = None)`
7. Uu tien ranking:
   - exact name match
   - case-insensitive name contains
   - path contains query
8. Viet test fixture nho co class, method, function, async function.

Done khi:

- Tim duoc `WorkspaceContextRetriever`, `ContextRetrieverPort`, `RunLocalLLMWorkflowUseCase`.
- Moi symbol co file va line range dung.
- Parser loi mot file khong lam hong toan bo index.

## Cap 3 - Trung binh: Imports

Muc tieu: agent biet file nao phu thuoc module nao, de chon context theo dependency gan nhat.

Steps:

1. Them `CodeImport` domain object.
2. Trong `PythonAstIndexer`, extract:
   - `import module`
   - `import module as alias`
   - `from module import name`
   - relative import voi `level`
3. Normalize import noi bo cua project:
   - `harness.core.domain` -> `src/harness/core/domain`
   - `harness.adapters.context` -> `src/harness/adapters/context`
4. Tao dependency map:
   - `file -> imported modules`
   - `module -> importer files`
5. Them query:
   - `imports_for_file(path)`
   - `importers_of(module_or_file)`
6. Cap nhat context retriever ranking:
   - neu task match mot symbol, them file dinh nghia symbol
   - them 1-hop importer/imported files neu con token budget
7. Viet test cho absolute import, relative import, alias import.

Done khi:

- Hoi ve mot use case co the lay them port/domain lien quan.
- ContextPack khong chi dua file match keyword, ma co ca dependency truc tiep.

## Cap 4 - Trung binh: Class/function signatures

Muc tieu: local LLM doc "API map" truoc khi doc body, giam token va giam doan mo.

Steps:

1. Mo rong `CodeSymbol.signature`.
2. Lay signature tu source line:
   - function/method: tu `lineno` den dau `:`
   - class: `class Name(Base):`
3. Xu ly signature multi-line bang AST line range va cat den dong ket thuc header.
4. Tao output compact:
   - class name
   - method signatures
   - function signatures
   - file + line
5. Them query:
   - `symbol_outline(path)`
   - `api_map(paths: list[str])`
6. Cho `WorkspaceContextRetriever` chen `symbol_outline` truoc `code_chunk` khi file co nhieu code.
7. Viet test cho type hints, async function, dataclass, Protocol.

Done khi:

- Local LLM co the thay API cua `ContextRetrieverPort` ma khong can doc full body.
- File dai duoc tom tat bang outline truoc, body chi doc khi can.

## Cap 5 - Kho: Call graph

Muc tieu: tra loi "function A goi function nao?" va "neu sua function nay, duong goi nao bi anh huong?".

Steps:

1. Them `CodeCall` domain object:
   - caller symbol
   - callee name raw
   - callee resolved symbol optional
   - file, line, confidence
2. MVP dung AST visitor cho `ast.Call`.
3. Resolve don gian:
   - `foo()` -> function cung module hoac imported name
   - `self.foo()` -> method cung class
   - `module.foo()` -> imported module function neu map duoc
4. Gan confidence:
   - `high` cho local function / method resolve duoc
   - `medium` cho imported symbol resolve duoc
   - `low` cho dynamic call, attribute chain, unknown object
5. Them query:
   - `calls_from(symbol)`
   - `callers_of(symbol)`
   - `impact_radius(symbol, depth=1)`
6. Dung call graph de tang ranking context khi task la sua behavior.
7. Viet test cho direct call, self method call, imported function call.
8. Neu can do chinh xac cao hon, danh dau phase LSP hoac CodeQL.

Done khi:

- Co approximate call graph noi bo cho Python.
- Ket qua ghi confidence de LLM khong xem approximate nhu su that tuyet doi.

## Cap 6 - Kho: References / usages

Muc tieu: tra loi "symbol nay duoc dung o dau?" voi do tin cay cao hon text search.

Steps:

1. Them `CodeReference` feature object neu chua co tu Cap 1.
2. MVP:
   - dung symbol table de biet candidate names
   - dung ripgrep voi word boundary
   - loc comment/string neu AST co the ho tro
3. Phan loai usage:
   - definition
   - import
   - call
   - type annotation
   - attribute access
   - unknown text match
4. Them query:
   - `references_to(symbol)`
   - `usages_in_file(path)`
5. Ranking:
   - import/call > annotation > unknown text
   - file trong `src/` > `tests/` neu task sua runtime
   - `tests/` > `src/` neu task la them/sua test
6. Nang cap sau:
   - chay Pyright/Pylance LSP de lay references chinh xac
   - hoac sinh SCIP/LSIF neu muon Sourcegraph-style index
7. Viet test cho class imported o file khac, method call, type annotation.

Done khi:

- Sua mot port/use case co the liet ke tests va adapters dang dung no.
- References co type/confidence, khong chi la danh sach grep raw.

## Cap 7 - Rat kho: Data flow va security flow

Muc tieu: phan tich duong di cua du lieu nhay cam, user input, file IO, network IO, command execution.

Day khong nen nam trong MVP cua repo hien tai. Chi lam khi co threat model hoac rule cu the.

Steps:

1. Xac dinh sources:
   - user request
   - LLM raw output
   - file content
   - env/config
   - tool call arguments
2. Xac dinh sinks:
   - shell/tool executor
   - file write
   - network request
   - prompt payload
   - logs
3. Xac dinh sanitizers/validators:
   - schema validation
   - allowlist path
   - approval gate
   - JSON validator
4. Viet rule Semgrep OSS cho pattern don gian truoc.
5. Neu can interprocedural flow, them CodeQL database cho Python.
6. Tich hop report vao harness:
   - `SecurityFinding`
   - severity
   - source -> sink path
   - suggested mitigation
7. Khong dua finding low-confidence truc tiep cho local LLM nhu fact; phai co tag `analysis_confidence`.
8. Viet regression tests bang sample vulnerable files.

Done khi:

- Co it nhat mot rule source-to-sink chay duoc trong CI/local.
- Finding co file/line/source/sink ro rang.
- False positive duoc danh dau va khong chan workflow neu chua dat nguong severity.

## Lo trinh thuc thi de xuat

### Milestone 1: MVP file index

Pham vi: Cap 1.

Steps:

1. Tao domain + port cho code index.
2. Implement filesystem indexer.
3. Ket noi optional vao `WorkspaceContextRetriever`.
4. Them tests cho file tree, search, read chunk.

Ket qua: local LLM chon file tot hon, it doc thua hon.

### Milestone 2: Python structure index

Pham vi: Cap 2, 3, 4.

Steps:

1. Implement Python AST symbol extractor.
2. Extract imports va signatures.
3. Tao query service de tra ve `symbol_outline` va `api_map`.
4. Cap nhat context retriever de dua outline vao ContextPack.
5. Them tests cho core/use_cases, core/ports, adapters/context.

Ket qua: agent co ban do API cua repo truoc khi doc body.

### Milestone 3: Approximate relationship index

Pham vi: Cap 5, 6.

Steps:

1. Implement AST call extractor.
2. Resolve local calls voi confidence.
3. Implement references/usages bang symbol table + ripgrep.
4. Them ranking theo dependency, caller/callee va tests.

Ket qua: agent co the uoc luong blast radius khi sua code.

### Milestone 4: Advanced analysis

Pham vi: Cap 7.

Steps:

1. Viet threat model nho cho harness.
2. Chon Semgrep rule hay CodeQL theo nhu cau.
3. Tich hop finding vao report rieng, khong tron voi code context thuong.

Ket qua: harness co lop phan tich security/data flow rieng.

## Thu tu uu tien cho project hien tai

1. Lam ngay: File tree + text search, vi `WorkspaceContextRetriever` hien da co logic tuong tu va co test.
2. Lam tiep: Python symbols/imports/signatures bang `ast`, vi repo la Python 3.12 va chua can dependency nang.
3. Lam sau: references bang ripgrep + symbol table, vi gia tri cao cho local LLM nhung van kha de quan ly.
4. Lam khi can: call graph approximate.
5. Chua lam neu chua co yeu cau bao mat cu the: data flow/security flow.

## Ranh gioi khong lam trong MVP

- Khong dung LLM de parse code.
- Khong index file binary, cache, generated artifact.
- Khong yeu cau database ngoai nhu Postgres/Elasticsearch.
- Khong can LSP server o giai doan dau.
- Khong coi call graph/reference MVP la chinh xac tuyet doi.

## Tieu chi hoan thanh chung

- Tat ca index record deu co source file va line number neu co the.
- Parser loi mot file thi log/collect diagnostic, khong fail ca repo.
- Moi query tra ve ket qua co ranking va confidence khi approximate.
- ContextPack tao ra nho hon token budget va uu tien outline truoc body.
- Co tests cho tung cap truoc khi cap do cao hon dua vao no.
