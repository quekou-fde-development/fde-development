#!/usr/bin/env python3
"""Exercise the real feedback kernel and production guards with offline fixtures.

The pure kernel is driven through an in-memory six-method adapter for its
fault-injection protocol.  Scenarios that depend on durable Journal state or
RemoteEffectAdapter guards use the real production implementation with the
package's isolated FixtureGitHub transport.  No network client is invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Callable
import uuid


sys.dont_write_bytecode = True

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_ROOT = _PACKAGE_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))
import kernel as production_kernel

FAULT_POINTS = (
    "after_intent_before_effect",
    "after_effect_before_receipt",
    "after_receipt_before_commit",
    "during_unlock",
)
SCENARIOS = (
    "duplicate_attempt",
    "unknown_external_state",
    "stale_lock",
    "backlog_retry",
    "evidence_missing",
    "cross_target_isolation",
)
BOUNDARIES = ("create_issue", "add_comment", "patch_issue")
WITH_EFFECT = ["INTENT", "READBACK", "EFFECT", "RECEIPT", "READBACK", "COMMIT", "UNLOCK"]
WITHOUT_EFFECT = ["INTENT", "READBACK", "RECEIPT", "READBACK", "COMMIT", "UNLOCK"]
SAFE_ID = re.compile(r"[A-Za-z0-9_.-]+\Z")


class RunnerError(RuntimeError):
    pass


class InjectedCrash(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(131072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def ensure_one_shot_run_dir(raw: str) -> Path:
    run_dir = Path(raw).expanduser().resolve()
    if run_dir.exists():
        if not run_dir.is_dir():
            raise RunnerError("--run-dir 必须是目录")
        if any(run_dir.iterdir()):
            raise RunnerError("--run-dir 必须为空的一次性目录")
    else:
        run_dir.mkdir(parents=True, mode=0o700)
    return run_dir


def write_json(run_dir: Path, relative: str, value: Any) -> dict[str, str]:
    if not SAFE_ID.fullmatch(relative.replace("/", "-")):
        raise RunnerError("evidence 名称不安全")
    destination = (run_dir / relative).resolve()
    try:
        destination.relative_to(run_dir)
    except ValueError as error:
        raise RunnerError("evidence 路径越出 run-dir") from error
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = json_bytes(value)
    descriptor, temporary = tempfile.mkstemp(prefix=".stateful-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": relative, "sha256": hashlib.sha256(data).hexdigest()}


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as error:
        raise RunnerError("--contract 不是可读 JSON 对象") from error
    if not isinstance(payload, dict):
        raise RunnerError("--contract 顶层必须为对象")
    return payload


def _restore_modules(previous: dict[str, Any]) -> None:
    for name, value in previous.items():
        if value is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = value


def _module_from_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RunnerError("无法加载 " + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_real_modules(package: Path) -> tuple[Any, Any, Any, Any, Path, Path, dict[str, Any]]:
    """Load one coherent set of production modules and its offline transport."""
    scripts = package / "scripts"
    kernel_path = scripts / "kernel.py"
    entry_path = scripts / "entrypoints.py"
    feedback_path = scripts / "feedback.py"
    fixture_path = scripts / "fixture_transport.py"
    if not all(path.is_file() for path in (kernel_path, entry_path, feedback_path, fixture_path)):
        raise RunnerError("找不到 kernel、entrypoint、feedback 或离线 fixture")
    previous = {name: sys.modules.get(name) for name in
                ("kernel", "entrypoints", "feedback", "fixture_transport")}
    try:
        kernel = production_kernel
        if Path(kernel.__file__).resolve() != kernel_path.resolve():
            raise RunnerError("静态导入的 kernel 未绑定当前包 scripts/kernel.py")
        entry = _module_from_path("entrypoints", entry_path)
        feedback = _module_from_path("feedback", feedback_path)
        fixture = _module_from_path("fixture_transport", fixture_path)
    except Exception:
        _restore_modules(previous)
        raise
    if not callable(getattr(kernel, "apply_transaction", None)):
        raise RunnerError("真实 kernel 缺 apply_transaction")
    if not callable(getattr(entry, "apply_feedback_effect", None)):
        raise RunnerError("真实 entrypoint 缺 apply_feedback_effect")
    if not callable(getattr(feedback, "transaction", None)) or \
            not callable(getattr(feedback, "RemoteEffectAdapter", None)) or \
            not callable(getattr(fixture, "FixtureGitHub", None)):
        raise RunnerError("生产 feedback 或离线 FixtureGitHub 接口缺失")
    return kernel, entry, feedback, fixture, kernel_path, entry_path, previous


class FakeEffectAdapter:
    """Records actual protocol calls and injects one crash at a lifecycle edge."""

    def __init__(self, fault: str | None = None, unknown_targets: set[str] | None = None):
        self.fault = fault
        self.unknown_targets = set(unknown_targets or ())
        self.fault_fired = False
        self.events: list[str] = []
        self.event_details: list[dict[str, Any]] = []
        self.applied: set[str] = set()
        self.effect_calls = 0
        self.context: dict[str, Any] = {}

    def set_context(self, logical_target: str, evidence_revision: str, attempt_id: str,
                    fence_token: int) -> None:
        self.context = {
            "logical_target": logical_target,
            "evidence_revision": evidence_revision,
            "attempt_id": attempt_id,
            "fence_token": fence_token,
        }

    def _record(self, event: str, key: str) -> None:
        self.events.append(event)
        self.event_details.append({"event": event, "key": key, "context": dict(self.context)})

    def _inject(self, fault_point: str) -> None:
        if self.fault == fault_point and not self.fault_fired:
            self.fault_fired = True
            raise InjectedCrash(fault_point)

    def intent(self, key: str) -> None:
        self._record("INTENT", key)
        self._inject("after_intent_before_effect")

    def effect(self, key: str) -> None:
        self.effect_calls += 1
        self.applied.add(key)
        self._record("EFFECT", key)
        self._inject("after_effect_before_receipt")

    def receipt(self, key: str) -> None:
        self._record("RECEIPT", key)
        self._inject("after_receipt_before_commit")

    def readback(self, key: str) -> str:
        self._record("READBACK", key)
        if key in self.unknown_targets and key not in self.applied:
            return "UNKNOWN"
        return "APPLIED" if key in self.applied else "ABSENT"

    def commit(self, key: str) -> None:
        self._record("COMMIT", key)

    def unlock(self, key: str) -> None:
        self._record("UNLOCK", key)
        self._inject("during_unlock")


def invoke_kernel(kernel: Any, adapter: FakeEffectAdapter, logical_target: str,
                  evidence_revision: str, attempt_id: str, fence_token: int,
                  fault_point: str | None, run_dir: Path) -> dict[str, Any]:
    if kernel is not production_kernel:
        raise RunnerError("runner kernel 对象与静态绑定不一致")
    adapter.set_context(logical_target, evidence_revision, attempt_id, fence_token)
    result = production_kernel.apply_transaction(logical_target, evidence_revision, attempt_id,
                                                 fence_token, adapter, fault_point, str(run_dir))
    if not isinstance(result, dict):
        raise RunnerError("真实 kernel 未返回对象")
    return result


def invoke_entrypoint(entry: Any, kernel_path: Path, adapter: FakeEffectAdapter,
                      logical_target: str, evidence_revision: str, attempt_id: str,
                      fence_token: int) -> dict[str, Any]:
    del kernel_path
    adapter.set_context(logical_target, evidence_revision, attempt_id, fence_token)
    result = entry.apply_feedback_effect(logical_target, evidence_revision, attempt_id,
                                         fence_token, adapter)
    if not isinstance(result, dict):
        raise RunnerError("真实 entrypoint 未返回对象")
    return result


def entry_identity_ok(entry: Any, kernel: Any) -> bool:
    return entry.apply_feedback_effect.__globals__.get("apply_transaction") is kernel.apply_transaction


def state_of(result: dict[str, Any] | None) -> str | None:
    return result.get("state") if isinstance(result, dict) else None


def production_config(feedback: Any) -> dict[str, Any]:
    return {
        "repository": feedback.REPO,
        "expected_actor": "fixture-bot",
        "approvers": ["trusted-fixture-user"],
        "maintainer_actors": ["fixture-bot"],
        "maintainer_approvers": ["trusted-fixture-user"],
    }


def preview_for(feedback: Any, scenario: str, variant: str = "primary") -> tuple[dict[str, Any], dict[str, Any]]:
    """Create only synthetic public fixture content, with a stable UUID per case."""
    request = str(uuid.uuid5(uuid.NAMESPACE_URL, "feedback-stateful-runner/" + scenario + "/" + variant))
    draft = {
        "request_id": request,
        "source_alias": "offline fixture",
        "project": "stateful verification fixture",
        "category": "手册问题",
        "target": "fixture/stateful/" + scenario + "/" + variant,
        "title": "Stateful fixture " + scenario + " " + variant,
        "description": "Offline fixture observes durable state for " + scenario + " " + variant + ".",
        "expected": "The isolated fixture preserves one safe effect and a readback receipt.",
        "evidence": "",
    }
    preview = feedback.wrap_preview(feedback.render(draft))
    approval = {
        "approved": True,
        "approved_by": "trusted-fixture-user",
        "approved_at": feedback.now(),
        "preview_sha256": preview["preview_sha256"],
    }
    return preview, approval


def capture_stop(feedback: Any, operation: Callable[[], Any]) -> tuple[Any | None, str | None]:
    try:
        return operation(), None
    except feedback.Stop as error:
        return None, error.code


def load_journal_entry(feedback: Any, state_dir: Path, request: str) -> dict[str, Any] | None:
    with feedback.Journal(state_dir) as journal:
        return journal.load(request)


def trace_adapter_methods(adapter: Any) -> list[str]:
    """Record actual adapter method invocations without replacing its behavior."""
    events: list[str] = []
    for name in ("intent", "readback", "effect", "receipt", "commit", "unlock"):
        original = getattr(adapter, name)

        def wrapped(key: str, _original: Callable[[str], Any] = original,
                    _event: str = name.upper()) -> Any:
            events.append(_event)
            return _original(key)

        setattr(adapter, name, wrapped)
    return events


def fault_case(fault_id: str, kernel: Any, run_dir: Path) -> tuple[bool, dict[str, Any]]:
    target = "fault-" + fault_id
    adapter = FakeEffectAdapter(fault=fault_id)
    crash_trace: list[str]
    crashed = False
    try:
        invoke_kernel(kernel, adapter, target, "revision-fault", "attempt-first", 1,
                      fault_id, run_dir)
    except InjectedCrash:
        crashed = True
    crash_trace = list(adapter.events)
    adapter.fault = None
    recovery_start = len(adapter.events)
    result = invoke_kernel(kernel, adapter, target, "revision-fault", "attempt-recovery", 2,
                           None, run_dir)
    recovery_trace = adapter.events[recovery_start:]
    expected_recovery = WITH_EFFECT if fault_id == "after_intent_before_effect" else WITHOUT_EFFECT
    passed = (crashed and state_of(result) == "COMMITTED" and len(adapter.applied) == 1 and
              adapter.effect_calls == 1 and recovery_trace == expected_recovery)
    evidence = {
        "id": fault_id,
        "kind": "fault_point",
        "crashed": crashed,
        "crash_trace": crash_trace,
        "recovery_trace": recovery_trace,
        "events": recovery_trace,
        "effect_count": adapter.effect_calls,
        "applied_keys": sorted(adapter.applied),
        "terminal_state": state_of(result),
        "event_details": adapter.event_details,
    }
    return passed, evidence


def duplicate_attempt_case(kernel: Any, _entry: Any, _feedback: Any, _fixture: Any,
                           run_dir: Path) -> tuple[bool, dict[str, Any]]:
    target = "scenario-duplicate"
    adapter = FakeEffectAdapter()
    first_start = len(adapter.events)
    first = invoke_kernel(kernel, adapter, target, "revision-duplicate", "attempt-1", 1, None, run_dir)
    first_trace = adapter.events[first_start:]
    second_start = len(adapter.events)
    second = invoke_kernel(kernel, adapter, target, "revision-duplicate", "attempt-2", 2, None, run_dir)
    second_trace = adapter.events[second_start:]
    passed = (state_of(first) == "COMMITTED" and state_of(second) == "COMMITTED" and
              len(adapter.applied) == 1 and adapter.effect_calls == 1 and
              first_trace == WITH_EFFECT and second_trace == WITHOUT_EFFECT)
    return passed, {
        "id": "duplicate_attempt", "kind": "scenario", "events": second_trace,
        "first_trace": first_trace, "second_trace": second_trace,
        "effect_count": adapter.effect_calls, "winner_count": 1 if passed else 0,
        "terminal_state": state_of(second), "event_details": adapter.event_details,
    }


def unknown_external_state_case(kernel: Any, _entry: Any, _feedback: Any, _fixture: Any,
                                run_dir: Path) -> tuple[bool, dict[str, Any]]:
    target = "scenario-unknown"
    adapter = FakeEffectAdapter(unknown_targets={target})
    result = invoke_kernel(kernel, adapter, target, "revision-unknown", "attempt-1", 1, None, run_dir)
    passed = (state_of(result) == "RECONCILE_REQUIRED" and adapter.effect_calls == 0 and
              adapter.events == ["INTENT", "READBACK"])
    return passed, {
        "id": "unknown_external_state", "kind": "scenario", "events": list(adapter.events),
        "effect_count": adapter.effect_calls, "terminal_state": state_of(result),
        "replayed": False, "event_details": adapter.event_details,
    }


def stale_lock_case(kernel: Any, entry: Any, feedback: Any, fixture: Any,
                    run_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Use the real Journal and RemoteEffectAdapter guard to reject an old owner."""
    state_dir = run_dir / "journal-stale-lock"
    api = fixture.FixtureGitHub()
    config = production_config(feedback)
    preview, approval = preview_for(feedback, "stale-lock")
    winner, winner_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, preview, approval, state_dir))
    payload = preview["payload"]
    rid = payload["request_id"]
    winner_entry = load_journal_entry(feedback, state_dir, rid)
    stale_events: list[str] = []
    stale_error: str | None = None
    stale_effect_calls = 0
    replacement: dict[str, Any] | None = None
    if winner_entry:
        stale_entry = dict(winner_entry, phase="PREPARED")
        replacement = dict(winner_entry, phase="PREPARED",
                           fence=winner_entry["fence"] + 1,
                           attempt_id="replacement-owner")
        with feedback.Journal(state_dir) as journal:
            journal.put(rid, replacement)
            adapter = feedback.RemoteEffectAdapter(api, payload, stale_entry, journal, "create",
                                                   lambda *args, **kwargs: None)
            stale_events = trace_adapter_methods(adapter)
            writes_before = len(api.writes)
            try:
                entry.apply_feedback_effect(rid + ":create", feedback.digest(payload),
                                            stale_entry["attempt_id"], stale_entry["fence"], adapter)
            except feedback.Stop as error:
                stale_error = error.code
            stale_effect_calls = len(api.writes) - writes_before
    # A direct trusted-kernel probe remains part of every declared scenario.
    probe = FakeEffectAdapter()
    probe_result = invoke_kernel(kernel, probe, "stale-lock-probe", "fixture-revision",
                                 "fixture-attempt", 1, None, run_dir)
    winner_count = len(api.rows)
    old_fence_write_rejected = stale_error == "STALE_FENCE" and stale_effect_calls == 0
    passed = (winner_error is None and isinstance(winner, dict) and winner_count == 1 and
              old_fence_write_rejected and state_of(probe_result) == "COMMITTED" and
              probe.effect_calls == 1)
    return passed, {
        "id": "stale_lock", "kind": "scenario", "events": stale_events,
        "effect_count": len(api.writes), "stale_effect_calls": stale_effect_calls,
        "winner_count": winner_count, "old_fence_write_rejected": old_fence_write_rejected,
        "winner_receipt": winner, "winner_error": winner_error,
        "stale_terminal": stale_error, "replacement_owner": replacement,
        "kernel_probe_events": probe.events, "kernel_probe_state": state_of(probe_result),
        "actual_effect_calls": list(api.writes),
    }


def backlog_retry_case(kernel: Any, entry: Any, feedback: Any, fixture: Any,
                       run_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Exercise Journal.pending after real interrupted attempts and a later success."""
    del entry
    state_dir = run_dir / "journal-backlog-retry"
    api = fixture.FixtureGitHub()
    config = production_config(feedback)
    first_preview, first_approval = preview_for(feedback, "backlog-retry", "first")
    second_preview, second_approval = preview_for(feedback, "backlog-retry", "second")
    _, first_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, first_preview, first_approval,
                                                state_dir, fault="CREATE_INTENT"))
    _, second_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, second_preview, second_approval,
                                                state_dir, fault="CREATE_INTENT"))
    _, retry_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, first_preview, first_approval, state_dir))
    later_preview, later_approval = preview_for(feedback, "backlog-retry", "later-target")
    later_result, later_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, later_preview, later_approval, state_dir))
    with feedback.Journal(state_dir) as journal:
        first_selection = journal.pending()
        second_selection = journal.pending()
    expected_order = sorted(first_selection, key=lambda row: (row["created_at"], row["request_id"]))
    selected_ids = [row["request_id"] for row in first_selection]
    required_ids = [first_preview["payload"]["request_id"], second_preview["payload"]["request_id"]]
    reselected = all(request in selected_ids for request in required_ids) and second_selection == first_selection
    probe = FakeEffectAdapter()
    probe_result = invoke_kernel(kernel, probe, "backlog-retry-probe", "fixture-revision",
                                 "fixture-attempt", 1, None, run_dir)
    passed = (first_error == "INJECTED_CRASH" and second_error == "INJECTED_CRASH" and
              retry_error == "RECONCILE_REQUIRED" and later_error is None and
              isinstance(later_result, dict) and reselected and first_selection == expected_order and
              len(api.writes) == 1 and state_of(probe_result) == "COMMITTED" and probe.effect_calls == 1)
    return passed, {
        "id": "backlog_retry", "kind": "scenario", "events": ["CREATE_INTENT", "PENDING_SELECTOR"],
        "effect_count": 0, "unrelated_effect_calls": len(api.writes),
        "failed_attempt_errors": [first_error, second_error], "retry_terminal": retry_error,
        "later_target_receipt": later_result, "later_target_error": later_error,
        "selector": "Journal.pending", "first_selection": first_selection,
        "second_selection": second_selection, "stable_created_at_order": first_selection == expected_order,
        "reselected": reselected, "permanent_suppression": False,
        "kernel_probe_events": probe.events, "kernel_probe_state": state_of(probe_result),
        "actual_effect_calls": list(api.writes),
    }


def evidence_missing_case(kernel: Any, entry: Any, feedback: Any, fixture: Any,
                          run_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Remove fake remote evidence and verify transaction and adapter both halt."""
    state_dir = run_dir / "journal-evidence-missing"
    api = fixture.FixtureGitHub()
    config = production_config(feedback)
    preview, approval = preview_for(feedback, "evidence-missing")
    first, first_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, preview, approval, state_dir))
    payload = preview["payload"]
    rid = payload["request_id"]
    api.rows.clear()
    writes_before_retry = len(api.writes)
    _, missing_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, preview, approval, state_dir))
    retry_effect_calls = len(api.writes) - writes_before_retry
    current_entry = load_journal_entry(feedback, state_dir, rid)
    guard_events: list[str] = []
    guard_error: str | None = None
    guard_effect_calls = 0
    if current_entry:
        adapter_entry = dict(current_entry, phase="PREPARED")
        with feedback.Journal(state_dir) as journal:
            journal.put(rid, dict(current_entry, revision="evidence-revoked"))
            adapter = feedback.RemoteEffectAdapter(api, payload, adapter_entry, journal, "create",
                                                   lambda *args, **kwargs: None)
            guard_events = trace_adapter_methods(adapter)
            writes_before_guard = len(api.writes)
            try:
                entry.apply_feedback_effect(rid + ":create", feedback.digest(payload),
                                            adapter_entry["attempt_id"], adapter_entry["fence"], adapter)
            except feedback.Stop as error:
                guard_error = error.code
            guard_effect_calls = len(api.writes) - writes_before_guard
    probe = FakeEffectAdapter(unknown_targets={"evidence-missing-probe"})
    probe_result = invoke_kernel(kernel, probe, "evidence-missing-probe", "fixture-revision",
                                 "fixture-attempt", 1, None, run_dir)
    passed = (first_error is None and isinstance(first, dict) and missing_error == "RECONCILE_REQUIRED" and
              retry_effect_calls == 0 and guard_error == "RECONCILE_REQUIRED" and
              guard_effect_calls == 0 and state_of(probe_result) == "RECONCILE_REQUIRED" and
              probe.effect_calls == 0)
    return passed, {
        "id": "evidence_missing", "kind": "scenario", "events": guard_events,
        "effect_count": len(api.writes), "retry_effect_calls": retry_effect_calls,
        "revision_guard_effect_calls": guard_effect_calls,
        "terminal_state": "RECONCILE_REQUIRED" if missing_error == "RECONCILE_REQUIRED" else missing_error,
        "missing_remote_evidence": len(api.rows) == 0, "evidence_revision_checked": guard_error == "RECONCILE_REQUIRED",
        "first_receipt": first, "first_error": first_error, "retry_terminal": missing_error,
        "guard_terminal": guard_error, "kernel_probe_events": probe.events,
        "kernel_probe_state": state_of(probe_result), "actual_effect_calls": list(api.writes),
    }


def cross_target_isolation_case(kernel: Any, entry: Any, feedback: Any, fixture: Any,
                                run_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Submit two logical targets through the actual transaction and journal."""
    del entry
    state_dir = run_dir / "journal-cross-target"
    api = fixture.FixtureGitHub()
    config = production_config(feedback)
    left_preview, left_approval = preview_for(feedback, "cross-target", "left")
    right_preview, right_approval = preview_for(feedback, "cross-target", "right")
    left, left_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, left_preview, left_approval, state_dir))
    writes_after_left = len(api.writes)
    right, right_error = capture_stop(
        feedback, lambda: feedback.transaction(api, config, right_preview, right_approval, state_dir))
    left_entry = load_journal_entry(feedback, state_dir, left_preview["payload"]["request_id"])
    right_entry = load_journal_entry(feedback, state_dir, right_preview["payload"]["request_id"])
    left_number = left.get("number") if isinstance(left, dict) else None
    right_number = right.get("number") if isinstance(right, dict) else None
    collision = (left_preview["payload"]["request_id"] == right_preview["payload"]["request_id"] or
                 left_number == right_number or left_entry == right_entry)
    probe_left, probe_right = FakeEffectAdapter(), FakeEffectAdapter()
    probe_left_result = invoke_kernel(kernel, probe_left, "cross-target-probe-left", "fixture-revision",
                                      "fixture-attempt-left", 1, None, run_dir)
    probe_right_result = invoke_kernel(kernel, probe_right, "cross-target-probe-right", "fixture-revision",
                                       "fixture-attempt-right", 1, None, run_dir)
    passed = (left_error is None and right_error is None and isinstance(left, dict) and isinstance(right, dict) and
              writes_after_left == 1 and len(api.writes) - writes_after_left == 1 and not collision and
              state_of(probe_left_result) == "COMMITTED" and state_of(probe_right_result) == "COMMITTED" and
              probe_left.effect_calls == 1 and probe_right.effect_calls == 1)
    return passed, {
        "id": "cross_target_isolation", "kind": "scenario", "events": ["CREATE_LEFT", "CREATE_RIGHT"],
        "effect_count": writes_after_left, "right_effect_count": len(api.writes) - writes_after_left,
        "actual_total_effect_calls": len(api.writes), "left_receipt": left, "right_receipt": right,
        "left_error": left_error, "right_error": right_error,
        "left_journal": left_entry, "right_journal": right_entry,
        "cross_target_collision": collision, "terminal_state": "COMMITTED" if passed else None,
        "kernel_probe": {"left": probe_left.events, "right": probe_right.events},
        "actual_effect_calls": list(api.writes),
    }


SCENARIO_RUNNERS: dict[str, Callable[[Any, Any, Any, Any, Path], tuple[bool, dict[str, Any]]]] = {
    "duplicate_attempt": duplicate_attempt_case,
    "unknown_external_state": unknown_external_state_case,
    "stale_lock": stale_lock_case,
    "backlog_retry": backlog_retry_case,
    "evidence_missing": evidence_missing_case,
    "cross_target_isolation": cross_target_isolation_case,
}


def binding_errors(contract: dict[str, Any], kernel_path: Path, entry_path: Path) -> list[str]:
    errors: list[str] = []
    expected_entry = {
        "path": "scripts/entrypoints.py",
        "symbol": "apply_feedback_effect",
        "kernel": "scripts/kernel.py::apply_transaction",
    }
    entries = contract.get("production_entrypoints")
    if entries != [{**expected_entry, "sha256": sha256_file(entry_path)}]:
        errors.append("production_entrypoints 未绑定真实 entrypoints.py::apply_feedback_effect")
    trusted = contract.get("tests", {}).get("trusted_entrypoint")
    if trusted != {"path": "scripts/kernel.py", "symbol": "apply_transaction"}:
        errors.append("trusted_entrypoint 未绑定真实 kernel.py::apply_transaction")
    bindings = contract.get("tests", {}).get("implementation_bindings")
    expected_bindings = [{"path": "scripts/kernel.py", "sha256": sha256_file(kernel_path),
                          "symbols": ["apply_transaction"]}]
    if bindings != expected_bindings:
        errors.append("implementation_bindings 未绑定真实 kernel 的当前 hash")
    boundary_ids = [row.get("id") for row in contract.get("effect_boundaries", [])
                    if isinstance(row, dict)]
    if set(boundary_ids) != set(BOUNDARIES) or len(boundary_ids) != len(BOUNDARIES):
        errors.append("effect_boundaries 必须精确声明 create_issue/add_comment/patch_issue")
    for row in contract.get("effect_boundaries", []):
        if isinstance(row, dict) and row.get("implementation_symbols") != ["scripts/kernel.py::apply_transaction"]:
            errors.append("effect boundary 未统一绑定真实 transaction kernel")
            break
    expected_faults = contract.get("tests", {}).get("fault_points")
    if expected_faults != list(FAULT_POINTS):
        errors.append("contract fault_points 未精确声明四个故障点")
    expected_scenarios = contract.get("tests", {}).get("scenarios")
    if expected_scenarios != list(SCENARIOS):
        errors.append("contract scenarios 未精确声明六个场景")
    return errors


def row_for(run_dir: Path, category: str, row_id: str, passed: bool,
            evidence: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not SAFE_ID.fullmatch(row_id):
        raise RunnerError("contract 条目 id 不安全")
    proof = write_json(run_dir, f"evidence/{category}-{row_id}.json", evidence)
    row = {"id": row_id, "status": "PASS" if passed else "FAIL", "evidence": proof}
    if extra:
        row.update(extra)
    return row


def run(contract_path: Path, run_dir: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    package = contract_path.parent.resolve()
    kernel, entry, feedback, fixture, kernel_path, entry_path, _previous = load_real_modules(package)
    errors = binding_errors(contract, kernel_path, entry_path)
    if not entry_identity_ok(entry, kernel):
        errors.append("entrypoint 未直接调用同一 kernel 函数对象")

    fault_rows: list[dict[str, Any]] = []
    declared_faults = contract.get("tests", {}).get("fault_points", [])
    for fault_id in declared_faults if isinstance(declared_faults, list) else []:
        if fault_id not in FAULT_POINTS:
            evidence = {"id": fault_id, "kind": "fault_point", "events": [], "effect_count": 0,
                        "reason": "未实现的 contract fault point"}
            fault_rows.append(row_for(run_dir, "fault", fault_id, False, evidence))
            continue
        passed, evidence = fault_case(fault_id, kernel, run_dir)
        fault_rows.append(row_for(run_dir, "fault", fault_id, passed, evidence))

    scenario_rows: list[dict[str, Any]] = []
    declared_scenarios = contract.get("tests", {}).get("scenarios", [])
    for scenario_id in declared_scenarios if isinstance(declared_scenarios, list) else []:
        runner = SCENARIO_RUNNERS.get(scenario_id)
        if runner is None:
            evidence = {"id": scenario_id, "kind": "scenario", "events": [], "effect_count": 0,
                        "reason": "未实现的 contract scenario"}
            scenario_rows.append(row_for(run_dir, "scenario", scenario_id, False, evidence))
            continue
        passed, evidence = runner(kernel, entry, feedback, fixture, run_dir)
        scenario_rows.append(row_for(run_dir, "scenario", scenario_id, passed, evidence))

    boundary_rows: list[dict[str, Any]] = []
    declared_boundaries = contract.get("effect_boundaries", [])
    for boundary in declared_boundaries if isinstance(declared_boundaries, list) else []:
        boundary_id = boundary.get("id") if isinstance(boundary, dict) else None
        if not isinstance(boundary_id, str):
            errors.append("effect boundary 缺 id")
            continue
        adapter = FakeEffectAdapter()
        try:
            result = invoke_entrypoint(entry, kernel_path, adapter,
                                       "boundary-" + boundary_id,
                                       "revision-" + boundary_id,
                                       "attempt-" + boundary_id, 1)
            passed = (state_of(result) == "COMMITTED" and entry_identity_ok(entry, kernel) and
                      adapter.events == WITH_EFFECT and adapter.effect_calls == 1 and
                      len(adapter.applied) == 1)
            evidence = {
                "id": boundary_id, "kind": "effect_boundary", "events": list(adapter.events),
                "effect_count": adapter.effect_calls, "applied_keys": sorted(adapter.applied),
                "terminal_state": state_of(result), "entry_call_completed": True,
                "entry_uses_kernel_identity": entry_identity_ok(entry, kernel),
                "event_details": adapter.event_details,
            }
        except Exception as error:  # Captured as evidence; no synthetic PASS is possible.
            passed = False
            evidence = {"id": boundary_id, "kind": "effect_boundary", "events": [],
                        "effect_count": 0, "error": type(error).__name__ + ": " + str(error)}
        symbols = boundary.get("implementation_symbols") if isinstance(boundary, dict) else None
        boundary_rows.append(row_for(run_dir, "boundary", boundary_id, passed, evidence,
                                     {"implementation_symbols": symbols}))

    all_rows = fault_rows + scenario_rows + boundary_rows
    status = "PASS" if not errors and all(row["status"] == "PASS" for row in all_rows) else "FAIL"
    return {
        "schema_version": 1,
        "status": status,
        "contract_sha256": sha256_file(contract_path),
        "implementation_bindings": contract.get("tests", {}).get("implementation_bindings"),
        "actual_bindings": {
            "kernel": {"path": "scripts/kernel.py", "sha256": sha256_file(kernel_path),
                       "symbol": "apply_transaction"},
            "entrypoint": {"path": "scripts/entrypoints.py", "sha256": sha256_file(entry_path),
                           "symbol": "apply_feedback_effect",
                           "kernel": "scripts/kernel.py::apply_transaction"},
        },
        "binding_errors": errors,
        "fault_points": fault_rows,
        "scenarios": scenario_rows,
        "boundary_results": boundary_rows,
        "summary": {
            "rows": len(all_rows),
            "passed": sum(row["status"] == "PASS" for row in all_rows),
            "failed": sum(row["status"] != "PASS" for row in all_rows),
        },
    }


def emit_report(run_dir: Path, report: dict[str, Any]) -> None:
    report_path = run_dir / "stateful_test_report.json"
    encoded = json_bytes(report)
    report_path.write_bytes(encoded)
    sys.stdout.write(encoded.decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--json", action="store_true", required=True)
    args = parser.parse_args()
    run_dir: Path | None = None
    try:
        run_dir = ensure_one_shot_run_dir(args.run_dir)
        report = run(Path(args.contract).expanduser().resolve(), run_dir)
    except Exception as error:
        report = {
            "schema_version": 1,
            "status": "FAIL",
            "contract_sha256": None,
            "error": type(error).__name__ + ": " + str(error),
            "fault_points": [], "scenarios": [], "boundary_results": [],
        }
    if run_dir is not None:
        emit_report(run_dir, report)
    else:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
