"""Regression tests for process observation and watchdog target addressing."""

from __future__ import annotations

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("platform", ["darwin", "linux"])
def test_process_snapshot_keeps_a_working_path_ps(monkeypatch, platform):
    from harness import lane_watchdog

    def run(command, **kwargs):
        assert command[0] == "ps"
        return subprocess.CompletedProcess(
            command, 0, "12 1 Wed Nov 25 17:00:00 2026 S 0:00.05\n", "",
        )

    monkeypatch.setattr(lane_watchdog.sys, "platform", platform)
    monkeypatch.setattr(lane_watchdog.subprocess, "run", run)

    assert lane_watchdog.process_snapshot() == {
        12: {"pid": 12, "ppid": 1, "started": "Wed Nov 25 17:00:00 2026", "state": "S",
             "cpu": "0:00.05"},
    }


@pytest.mark.parametrize(("platform", "exit_code", "diagnostic", "retry"), [
    ("darwin", 0, "ps: time: requires entitlement", True),
    ("darwin", 1, "ps: time: requires entitlement", True),
    ("darwin", 1, "ps: permission denied", False),
    ("linux", 1, "ps: time: requires entitlement", False),
])
def test_process_snapshot_retries_only_the_macos_time_entitlement_error(
    monkeypatch, platform, exit_code, diagnostic, retry,
):
    from harness import lane_watchdog

    commands = []

    def run(command, **kwargs):
        commands.append(command[0])
        if command[0] == "ps":
            return subprocess.CompletedProcess(command, exit_code, "", diagnostic)
        assert kwargs["timeout"] == 7
        return subprocess.CompletedProcess(
            command, 0, "12 1 Wed Nov 25 17:00:00 2026 S 0:00.05\n", "",
        )

    monkeypatch.setattr(lane_watchdog.sys, "platform", platform)
    monkeypatch.setattr(lane_watchdog.subprocess, "run", run)
    clock = iter((100.0, 103.0))
    monkeypatch.setattr(lane_watchdog, "time", SimpleNamespace(monotonic=clock.__next__))

    snapshot = lane_watchdog.process_snapshot()
    if retry:
        assert commands == ["ps", "/bin/ps"]
        assert snapshot is not None and snapshot[12]["cpu"] == "0:00.05"
    else:
        assert commands == ["ps"]
        assert snapshot is None


@pytest.mark.skipif(sys.platform != "darwin", reason="requires the macOS system ps")
def test_snapshot_reads_live_process_with_shadowed_ps(tmp_path, monkeypatch):
    from harness.lane_watchdog import process_snapshot

    shadow_ps = tmp_path / "ps"
    shadow_ps.write_text("#!/bin/sh\necho 'ps: time: requires entitlement' >&2\nexit 1\n")
    shadow_ps.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=os.pathsep)

    snapshot = process_snapshot()
    assert snapshot is not None
    row = snapshot[os.getpid()]
    assert row["ppid"] == os.getppid()
    assert row["started"] and row["cpu"]


def test_window_id_never_lets_tmux_fall_back_to_another_window() -> None:
    """tmux answers for the current window when a name is missing; resolve names to ids."""
    import subprocess

    from harness.lane_watchdog import stop_pane, window_id

    calls: list[tuple[str, ...]] = []

    def tmux(*arguments: str) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        out = "coder-a @6\nwatch-coder-a @7\n" if arguments[0] == "list-windows" else "0 0\n"
        return subprocess.CompletedProcess(list(arguments), 0, out, "")

    assert window_id("msg-r2:coder-a", tmux) == "@6"
    assert window_id("msg-r2:coder-b", tmux) is None
    assert window_id("msg-r2:@6", tmux) == "msg-r2:@6"
    calls.clear()
    assert "not found" in stop_pane("msg-r2:coder-b", tmux)
    assert all(call[0] == "list-windows" for call in calls)  # never addressed by name


def test_identity_signal_never_targets_reused_or_unknown_process():
    import signal

    import pytest

    from harness.lane_watchdog import signal_identity

    identity = {'pid': 90001, 'started': 'old'}
    sent = []
    table = {90001: {'pid': 90001, 'ppid': 1, 'started': 'new', 'state': 'S'}}
    assert signal_identity(identity, signal.SIGSTOP, processes=lambda: table,
                           send=lambda *args: sent.append(args)) == 'exited'
    assert not sent
    with pytest.raises(OSError, match='unavailable'):
        signal_identity(identity, signal.SIGSTOP, processes=lambda: None,
                        send=lambda *args: sent.append(args))
    assert not sent


def test_stop_pane_refuses_changed_recorded_identity(monkeypatch):
    import subprocess

    from harness import lane_watchdog

    table = {101: {'pid': 101, 'ppid': 1, 'started': 'new', 'state': 'S'}}
    monkeypatch.setattr(lane_watchdog, 'process_snapshot', lambda: table)
    def tmux(*a):
        return subprocess.CompletedProcess(
            a, 0, 'coder @1\n' if a[0] == 'list-windows' else '101 0\n', '')
    import pytest

    with pytest.raises(OSError, match='recorded identity'):
        lane_watchdog.stop_pane('run:coder', tmux, expected={'pid': 101, 'started': 'old'})


def test_dead_pane_stop_includes_previously_observed_orphans(monkeypatch):
    import signal
    import subprocess

    from harness import lane_watchdog

    table = {102: {'pid': 102, 'ppid': 1, 'started': 'orphan', 'state': 'S'}}
    known = [{'pid': 101, 'started': 'root'}, {'pid': 102, 'started': 'orphan'}]
    sent = []
    monkeypatch.setattr(lane_watchdog, 'process_snapshot', lambda: table)
    monkeypatch.setattr(lane_watchdog, 'signal_identity', lambda i, s: sent.append((i, s)))

    def tmux(*a):
        return subprocess.CompletedProcess(
            a, 0, 'coder @1\n' if a[0] == 'list-windows' else '101 1\n', '')

    lane_watchdog.stop_pane('run:coder', tmux, expected=known[0], known=known)
    assert (known[1], signal.SIGTERM) in sent
