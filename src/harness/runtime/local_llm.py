from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.adapters.context import WorkspaceContextRetriever
from harness.adapters.logging import LLMTextLogWriter
from harness.adapters.llm import LMStudioConfig, LMStudioLLMAdapter
from harness.core.services import LocalLLMJsonWorker, LocalWorkflowValidator
from harness.core.use_cases import LocalWorkflowPromptSet, RunLocalLLMWorkflowUseCase
from harness.features.code_index import FilesystemCodeIndexer


@dataclass(frozen=True, slots=True)
class LocalLLMWorkflowRuntime:
    llm: LMStudioLLMAdapter
    run_workflow: RunLocalLLMWorkflowUseCase
    text_log_path: Path | None = None


def build_local_llm_workflow_runtime(
    *,
    workspace_root: str | Path,
    base_url: str = "http://localhost:1234/v1",
    model: str | None = None,
    temperature: float = 0.1,
    timeout_seconds: float = 180.0,
    max_tokens: int | None = 2048,
    max_context_items: int = 8,
    text_log_path: str | Path | None = None,
) -> LocalLLMWorkflowRuntime:
    llm = LMStudioLLMAdapter(
        LMStudioConfig(
            base_url=base_url,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
    )
    prompts = load_local_llm_prompt_set()
    text_logger = LLMTextLogWriter(text_log_path) if text_log_path is not None else None
    code_index = FilesystemCodeIndexer(root=workspace_root)
    run_workflow = RunLocalLLMWorkflowUseCase(
        json_worker=LocalLLMJsonWorker(llm),
        context_retriever=WorkspaceContextRetriever(
            root=workspace_root,
            max_items=max_context_items,
            code_index=code_index,
        ),
        validator=LocalWorkflowValidator(),
        prompts=prompts,
        text_logger=text_logger,
    )

    return LocalLLMWorkflowRuntime(
        llm=llm,
        run_workflow=run_workflow,
        text_log_path=Path(text_log_path) if text_log_path is not None else None,
    )


def load_local_llm_prompt_set() -> LocalWorkflowPromptSet:
    prompt_dir = Path(__file__).resolve().parents[1] / "features" / "local_llm" / "prompts"
    return LocalWorkflowPromptSet(
        normalizer=(prompt_dir / "normalizer.md").read_text(encoding="utf-8"),
        decomposer=(prompt_dir / "decomposer.md").read_text(encoding="utf-8"),
        fact_extractor=(prompt_dir / "fact_extractor.md").read_text(encoding="utf-8"),
        planner=(prompt_dir / "planner.md").read_text(encoding="utf-8"),
        final_writer=(prompt_dir / "final_writer.md").read_text(encoding="utf-8"),
    )
