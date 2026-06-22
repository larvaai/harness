from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.core.domain import (
    Checkpoint,
    CheckpointReason,
    HookContext,
    HookPoint,
    HookResult,
    LifecycleEvent,
    RuntimeState,
)
from harness.core.ports import CheckpointStorePort, EventPublisherPort, HookRunnerPort


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    point: HookPoint
    event: LifecycleEvent
    hook_results: list[HookResult]
    checkpoint: Checkpoint | None = None


class LifecycleManager:
    def __init__(
        self,
        *,
        hook_runner: HookRunnerPort,
        event_publisher: EventPublisherPort,
        checkpoint_store: CheckpointStorePort,
    ) -> None:
        self._hook_runner = hook_runner
        self._event_publisher = event_publisher
        self._checkpoint_store = checkpoint_store
        self._latest_checkpoint_seq_by_run: dict[str, int] = {}

    async def reach(
        self,
        *,
        point: HookPoint,
        state: RuntimeState,
        payload: dict[str, Any] | None = None,
        checkpoint_reason: CheckpointReason | None = None,
    ) -> LifecycleTransition:
        context = HookContext(
            run_id=state.run_id,
            point=point,
            state=state,
            payload=payload or {},
        )
        event = LifecycleEvent.from_context(context)

        await self._event_publisher.publish(event)
        hook_results = await self._hook_runner.run(point, context)

        checkpoint: Checkpoint | None = None
        if checkpoint_reason is not None:
            checkpoint = await self._save_checkpoint(
                reason=checkpoint_reason,
                state=state,
            )
            await self._publish_state_saved(state=state, checkpoint=checkpoint)

        return LifecycleTransition(
            point=point,
            event=event,
            hook_results=hook_results,
            checkpoint=checkpoint,
        )

    async def _save_checkpoint(
        self,
        *,
        reason: CheckpointReason,
        state: RuntimeState,
    ) -> Checkpoint:
        checkpoint = Checkpoint.from_state(
            reason=reason,
            state=state,
            seq=await self._next_checkpoint_seq(state.run_id),
        )
        await self._checkpoint_store.save(checkpoint)
        return checkpoint

    async def _publish_state_saved(
        self,
        *,
        state: RuntimeState,
        checkpoint: Checkpoint,
    ) -> None:
        context = HookContext(
            run_id=state.run_id,
            point=HookPoint.ON_STATE_SAVED,
            state=state,
            payload={"checkpoint": checkpoint},
        )
        event = LifecycleEvent.from_context(context)

        await self._event_publisher.publish(event)
        await self._hook_runner.run(HookPoint.ON_STATE_SAVED, context)

    async def _next_checkpoint_seq(self, run_id: str) -> int:
        if run_id not in self._latest_checkpoint_seq_by_run:
            latest = await self._checkpoint_store.load_latest(run_id)
            self._latest_checkpoint_seq_by_run[run_id] = latest.seq if latest else 0

        self._latest_checkpoint_seq_by_run[run_id] += 1
        return self._latest_checkpoint_seq_by_run[run_id]
