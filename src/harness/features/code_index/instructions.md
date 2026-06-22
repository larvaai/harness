# Code Index Skill

Use this skill when an agent needs read-only knowledge of the workspace source tree.

Available tools:

- `code_index.list_files`
- `code_index.search_text`
- `code_index.read_file`

Rules:

- Prefer `code_index.search_text` before reading large files.
- Use `code_index.read_file` with line bounds when possible.
- Treat Level 1 search results as text-search evidence, not semantic or symbol-level truth.
- Never request paths outside the workspace root.
