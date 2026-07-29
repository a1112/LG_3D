import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils import watchdog_bootstrap


def _call_bootstrap(tmp_path, monkeypatch, *, entrypoint="__main__"):
    watchdog_path = tmp_path / "watchdog.py"
    watchdog_path.write_text("# test watchdog\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(watchdog_bootstrap.os, "execv",
                        lambda executable, args: calls.append(
                            (executable, args)))
    monkeypatch.setattr(watchdog_bootstrap.sys, "platform", "linux")
    result = watchdog_bootstrap.maybe_exec_watchdog(
        entrypoint,
        watchdog_path,
        child_environment="TEST_WATCHDOG_CHILD",
        disable_environment="TEST_DISABLE_AUTO_WATCHDOG",
        service_name="test service",
    )
    return result, calls


def test_direct_source_entrypoint_execs_watchdog(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_WATCHDOG_CHILD", raising=False)
    monkeypatch.delenv("TEST_DISABLE_AUTO_WATCHDOG", raising=False)
    monkeypatch.delenv("LG3D_DISABLE_AUTO_WATCHDOG", raising=False)

    result, calls = _call_bootstrap(tmp_path, monkeypatch)

    assert result is True
    assert calls == [(sys.executable, [
        sys.executable,
        str((tmp_path / "watchdog.py").resolve()),
    ])]


def test_windows_runs_watchdog_in_process_and_does_not_fall_through(
        tmp_path, monkeypatch):
    watchdog_path = tmp_path / "watchdog.py"
    watchdog_path.write_text("# test watchdog\n", encoding="utf-8")
    run_calls = []
    exec_calls = []
    monkeypatch.setattr(watchdog_bootstrap.sys, "platform", "win32")
    monkeypatch.setattr(
        watchdog_bootstrap.runpy,
        "run_path",
        lambda path, run_name: run_calls.append((path, run_name)),
    )
    monkeypatch.setattr(
        watchdog_bootstrap.os,
        "execv",
        lambda executable, args: exec_calls.append((executable, args)),
    )

    with pytest.raises(SystemExit) as exc_info:
        watchdog_bootstrap.maybe_exec_watchdog(
            "__main__",
            watchdog_path,
            child_environment="TEST_WATCHDOG_CHILD",
            disable_environment="TEST_DISABLE_AUTO_WATCHDOG",
            service_name="test service",
        )

    assert exc_info.value.code == 0
    assert run_calls == [(str(watchdog_path.resolve()), "__main__")]
    assert exec_calls == []


def test_imported_or_supervised_entrypoint_does_not_recurse(tmp_path,
                                                            monkeypatch):
    result, calls = _call_bootstrap(tmp_path,
                                    monkeypatch,
                                    entrypoint="service_module")
    assert result is False
    assert calls == []

    monkeypatch.setenv("TEST_WATCHDOG_CHILD", "1")
    result, calls = _call_bootstrap(tmp_path, monkeypatch)
    assert result is False
    assert calls == []


def test_auto_watchdog_can_be_disabled_for_debugging(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_DISABLE_AUTO_WATCHDOG", "true")
    result, calls = _call_bootstrap(tmp_path, monkeypatch)
    assert result is False
    assert calls == []


def test_missing_watchdog_falls_back_to_direct_service(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(watchdog_bootstrap.os, "execv",
                        lambda executable, args: calls.append(
                            (executable, args)))

    result = watchdog_bootstrap.maybe_exec_watchdog(
        "__main__",
        tmp_path / "missing.py",
        child_environment="TEST_WATCHDOG_CHILD",
        disable_environment="TEST_DISABLE_AUTO_WATCHDOG",
        service_name="test service",
    )

    assert result is False
    assert calls == []


@pytest.mark.parametrize(
    ("entrypoint", "child_environment"),
    [
        ("app/Server/Server.py", "LG3D_API_WATCHDOG_CHILD"),
        ("app/algorithm_runtime/main.py",
         "LG3D_ALGORITHM_3D_WATCHDOG_CHILD"),
        ("app/algorithm_runtime_2D/server.py",
         "LG3D_ALGORITHM_2D_WATCHDOG_CHILD"),
        ("app/algorithm_runtime_2D/main2d.py",
         "LG3D_ALGORITHM_2D_WATCHDOG_CHILD"),
        ("app/plcServer/main.py", "LG3D_PLC_WATCHDOG_CHILD"),
    ],
)
def test_source_entrypoints_are_wired_to_watchdog(entrypoint,
                                                   child_environment):
    source = (PROJECT_ROOT / entrypoint).read_text(encoding="utf-8")

    assert "maybe_exec_watchdog(" in source
    assert child_environment in source


def test_both_2d_entrypoints_share_single_runtime_lock():
    for entrypoint in (
            "app/algorithm_runtime_2D/server.py",
            "app/algorithm_runtime_2D/main2d.py",
    ):
        source = (PROJECT_ROOT / entrypoint).read_text(encoding="utf-8")
        assert 'SingletonLock("algorithm_runtime_2d")' in source


@pytest.mark.parametrize(
    "watchdog_path",
    [
        "app/Server/watchdog.py",
        "app/CapTrue/watchdog.py",
        "app/algorithm_runtime/watchdog.py",
        "app/algorithm_runtime_2D/watchdog.py",
    ],
)
def test_windows_watchdog_mutex_is_global_across_sessions(watchdog_path):
    source = (PROJECT_ROOT / watchdog_path).read_text(encoding="utf-8")

    assert '"Global\\\\LG3D_' in source
    assert '"Local\\\\LG3D_' not in source
