from __future__ import annotations

import asyncio

from harness.core.domain import (
    Checkpoint,
    CheckpointReason,
    HookContext,
    HookPoint,
    HookResult,
    LifecycleEvent,
    RuntimeState,
    Task,
)
from harness.core.services import LifecycleManager


class RecordingHookRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[HookPoint, HookContext]] = []

    async def run(self, point: HookPoint, context: HookContext) -> list[HookResult]:
        self.calls.append((point, context))
        return [HookResult(hook_name=f"record_{point.value}", point=point)]


class RecordingEventPublisher:
    def __init__(self) -> None:
        self.events: list[LifecycleEvent] = []

    async def publish(self, event: LifecycleEvent) -> None:
        self.events.append(event)


class RecordingCheckpointStore:
    def __init__(self, latest: Checkpoint | None = None) -> None:
        self.saved: list[Checkpoint] = []
        self.latest = latest

    async def save(self, checkpoint: Checkpoint) -> None:
        self.saved.append(checkpoint)
        self.latest = checkpoint

    async def load_latest(self, run_id: str) -> Checkpoint | None:
        if self.latest and self.latest.run_id == run_id:
            return self.latest
        return None


def test_reach_publishes_event_runs_hook_saves_checkpoint_and_fires_state_saved() -> None:
    async def scenario() -> None:
        hooks = RecordingHookRunner()
        events = RecordingEventPublisher()
        checkpoints = RecordingCheckpointStore()
        lifecycle = LifecycleManager(
            hook_runner=hooks,
            event_publisher=events,
            checkpoint_store=checkpoints,
        )
        state = RuntimeState.new(Task("hello"), run_id="run_1")

        transition = await lifecycle.reach(
            point=HookPoint.BEFORE_RUN,
            state=state,
            payload={"source": "test"},
            checkpoint_reason=CheckpointReason.RUN_STARTED,
        )

        assert transition.point == HookPoint.BEFORE_RUN
        assert transition.checkpoint is checkpoints.saved[0]
        assert [event.point for event in events.events] == [
            HookPoint.BEFORE_RUN,
            HookPoint.ON_STATE_SAVED,
        ]
        assert [point for point, _ in hooks.calls] == [
            HookPoint.BEFORE_RUN,
            HookPoint.ON_STATE_SAVED,
        ]
        assert checkpoints.saved[0].run_id == "run_1"
        assert checkpoints.saved[0].seq == 1
        assert checkpoints.saved[0].reason == CheckpointReason.RUN_STARTED
        assert checkpoints.saved[0].state_snapshot["run_id"] == "run_1"
        assert hooks.calls[1][1].payload["checkpoint"] is checkpoints.saved[0]

    asyncio.run(scenario())


def test_checkpoint_sequence_continues_from_latest_store_checkpoint() -> None:
    async def scenario() -> None:
        state = RuntimeState.new(Task("resume"), run_id="run_resume")
        existing = Checkpoint.from_state(
            reason=CheckpointReason.RUN_STARTED,
            state=state,
            seq=7,
        )
        checkpoints = RecordingCheckpointStore(latest=existing)
        lifecycle = LifecycleManager(
            hook_runner=RecordingHookRunner(),
            event_publisher=RecordingEventPublisher(),
            checkpoint_store=checkpoints,
        )

        await lifecycle.reach(
            point=HookPoint.BEFORE_LLM_CALL,
            state=state,
            checkpoint_reason=CheckpointReason.BEFORE_LLM_CALL,
        )

        assert checkpoints.saved[0].seq == 8

    asyncio.run(scenario())
