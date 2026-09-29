"""Tests for shared registry utilities."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

import registry_utils
from registry_utils import (
    extract_npm_package_name,
    extract_npm_package_version,
    extract_pypi_package_name,
    is_preview_version,
    load_quarantine,
    normalize_version,
    parse_preview_version,
    resolve_preview_entry,
    sanitize_agent_env,
    semver_sort_key,
    should_skip_dir,
    strip_preview,
    subprocess_group_kwargs,
    terminate_process_group,
    timed_read,
    timed_readline,
    version_tuple,
)


class TestExtractNpmPackageName:
    def test_scoped_with_version(self):
        assert extract_npm_package_name("@google/gemini-cli@0.30.0") == "@google/gemini-cli"

    def test_scoped_without_version(self):
        assert extract_npm_package_name("@google/gemini-cli") == "@google/gemini-cli"

    def test_unscoped_with_version(self):
        assert extract_npm_package_name("some-package@1.2.3") == "some-package"

    def test_unscoped_without_version(self):
        assert extract_npm_package_name("some-package") == "some-package"

    def test_empty_string(self):
        assert extract_npm_package_name("") == ""


class TestExtractNpmPackageVersion:
    def test_scoped_with_version(self):
        assert extract_npm_package_version("@google/gemini-cli@0.30.0") == "0.30.0"

    def test_scoped_without_version(self):
        assert extract_npm_package_version("@google/gemini-cli") is None

    def test_unscoped_with_version(self):
        assert extract_npm_package_version("some-package@1.2.3") == "1.2.3"

    def test_unscoped_without_version(self):
        assert extract_npm_package_version("some-package") is None


class TestExtractPypiPackageName:
    def test_with_double_equals(self):
        assert extract_pypi_package_name("some-package==1.2.3") == "some-package"

    def test_with_at_version(self):
        assert extract_pypi_package_name("some-package@1.2.3") == "some-package"

    def test_with_gte(self):
        assert extract_pypi_package_name("some-package>=1.0") == "some-package"

    def test_plain_name(self):
        assert extract_pypi_package_name("some-package") == "some-package"


class TestNormalizeVersion:
    def test_already_semver(self):
        assert normalize_version("1.2.3") == "1.2.3"

    def test_two_parts(self):
        assert normalize_version("1.2") == "1.2.0"

    def test_one_part(self):
        assert normalize_version("1") == "1.0.0"

    def test_four_parts_truncated(self):
        assert normalize_version("1.2.3.4") == "1.2.3"


class TestVersionTuple:
    def test_pads_short_versions(self):
        assert version_tuple("1") == (1, 0, 0)
        assert version_tuple("1.2") == (1, 2, 0)

    def test_keeps_extra_components(self):
        assert version_tuple("1.2.3.4") == (1, 2, 3, 4)

    def test_rejects_prerelease(self):
        with pytest.raises(ValueError):
            version_tuple("1.9.0-preview.1")


class TestParsePreviewVersion:
    def test_parses_preview(self):
        assert parse_preview_version("1.9.0-preview.3") == ((1, 9, 0), 3)

    def test_plain_release_is_not_preview(self):
        assert parse_preview_version("1.9.0") is None
        assert not is_preview_version("1.9.0")

    @pytest.mark.parametrize(
        "version",
        [
            "1.0-preview-1",
            "1.0-preview.1",
            "1.9.0-preview",
            "1.9.0-preview.",
            "1.9.0-rc.1",
            "1.9.0-next.1",
            "1.9.0+preview.1",
            "v1.9.0-preview.1",
            "",
        ],
    )
    def test_rejects_unsupported_shapes(self, version):
        assert parse_preview_version(version) is None
        assert not is_preview_version(version)


class TestSemverSortKey:
    def test_total_ordering(self):
        ordered = [
            "1.9.0-preview.2",
            "1.9.0-preview.10",
            "1.9.0",
            "1.9.1-preview.1",
            "1.9.1",
        ]
        assert sorted(ordered, key=semver_sort_key) == ordered

    def test_numeric_counter_comparison(self):
        assert semver_sort_key("1.9.0-preview.10") > semver_sort_key("1.9.0-preview.2")

    def test_prerelease_ranks_below_its_release(self):
        assert semver_sort_key("1.9.0-preview.99") < semver_sort_key("1.9.0")

    def test_release_ranks_below_next_prerelease(self):
        assert semver_sort_key("1.9.0") < semver_sort_key("1.9.1-preview.1")


def _agent(version: str, preview: dict | None = None) -> dict:
    agent = {
        "id": "codex-acp",
        "name": "Codex",
        "version": version,
        "description": "ACP adapter",
        "repository": "https://github.com/agentclientprotocol/codex-acp",
        "authors": ["OpenAI"],
        "license": "proprietary",
        "distribution": {
            "npx": {
                "package": f"@agentclientprotocol/codex-acp@{version}",
                "args": ["--stable-flag"],
            }
        },
    }
    if preview is not None:
        agent["preview"] = preview
    return agent


def _preview(version: str) -> dict:
    return {
        "version": version,
        "distribution": {"npx": {"package": f"@agentclientprotocol/codex-acp@{version}"}},
    }


class TestStripPreview:
    def test_removes_preview_block(self):
        agent = _agent("1.8.0", _preview("1.9.0-preview.1"))

        stripped = strip_preview(agent)

        assert "preview" not in stripped
        assert stripped["version"] == "1.8.0"
        assert "preview" in agent  # input untouched

    def test_no_preview_block_is_a_copy(self):
        agent = _agent("1.8.0")

        stripped = strip_preview(agent)

        assert stripped == agent
        assert stripped["distribution"] is not agent["distribution"]


class TestResolvePreviewEntry:
    def test_no_preview_block_returns_base_entry(self):
        agent = _agent("1.8.0")

        assert resolve_preview_entry(agent) == agent

    def test_preview_ahead_substitutes_version_and_distribution(self):
        agent = _agent("1.8.0", _preview("1.9.0-preview.1"))

        entry = resolve_preview_entry(agent)

        assert "preview" not in entry
        assert entry["version"] == "1.9.0-preview.1"
        assert entry["distribution"] == {
            "npx": {"package": "@agentclientprotocol/codex-acp@1.9.0-preview.1"}
        }
        for field in ("id", "name", "description", "repository", "authors", "license"):
            assert entry[field] == agent[field]
        assert list(entry.keys()) == [k for k in agent if k != "preview"]

    def test_stable_ahead_falls_back_to_base_entry(self):
        agent = _agent("1.9.1", _preview("1.9.0-preview.1"))

        entry = resolve_preview_entry(agent)

        assert entry == strip_preview(agent)
        assert entry["version"] == "1.9.1"

    def test_equal_versions_fall_back_to_base_entry(self):
        agent = _agent("1.9.1", _preview("1.9.1"))

        entry = resolve_preview_entry(agent)

        assert entry == strip_preview(agent)

    def test_plain_release_preview_ahead_is_substituted(self):
        agent = _agent("1.9.0", _preview("1.9.1"))

        entry = resolve_preview_entry(agent)

        assert entry["version"] == "1.9.1"
        assert entry["distribution"]["npx"]["package"].endswith("@1.9.1")
        assert "preview" not in entry

    def test_result_is_detached_from_input(self):
        agent = _agent("1.8.0", _preview("1.9.0-preview.1"))

        entry = resolve_preview_entry(agent)
        entry["distribution"]["npx"]["package"] = "mutated"

        assert agent["preview"]["distribution"]["npx"]["package"] != "mutated"


class TestLoadQuarantine:
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            assert load_quarantine(Path(d)) == {}

    def test_empty_object(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "quarantine.json"
            p.write_text("{}")
            assert load_quarantine(Path(d)) == {}

    def test_with_entries(self):
        with tempfile.TemporaryDirectory() as d:
            data = {"bad-agent": "broke auth", "other": "removed"}
            p = Path(d) / "quarantine.json"
            p.write_text(json.dumps(data))
            assert load_quarantine(Path(d)) == data

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "quarantine.json"
            p.write_text("not json")
            assert load_quarantine(Path(d)) == {}


class TestShouldSkipDir:
    def test_skips_hidden_runtime_dirs(self):
        assert should_skip_dir(".sandbox")
        assert should_skip_dir(".matrix-sandbox-debug")
        assert should_skip_dir(".protocol-matrix-goose-check")
        assert should_skip_dir(".tmp-junie-run")

    def test_keeps_agent_dirs(self):
        assert not should_skip_dir("codex-acp")


class TestSanitizeAgentEnv:
    def test_keeps_agent_specific_flags(self):
        env = sanitize_agent_env(
            {
                "VT_ACP_ENABLED": "1",
                "DROID_DISABLE_AUTO_UPDATE": "true",
            }
        )

        assert env == {
            "VT_ACP_ENABLED": "1",
            "DROID_DISABLE_AUTO_UPDATE": "true",
        }

    def test_drops_runner_credentials_and_launch_overrides(self):
        env = sanitize_agent_env(
            {
                "AGENT_FLAG": "1",
                "GITHUB_TOKEN": "secret",
                "GITHUB_WORKSPACE": "/repo",
                "HOME": "/tmp/evil",
                "LD_PRELOAD": "/tmp/hook.so",
                "PATH": "/tmp/bin",
                "RUNNER_TEMP": "/tmp/runner",
                "SSH_AUTH_SOCK": "/tmp/ssh.sock",
            }
        )

        assert env == {"AGENT_FLAG": "1"}

    def test_drops_reserved_names_case_insensitively(self):
        env = sanitize_agent_env(
            {
                "AGENT_FLAG": "1",
                "Path": "/tmp/bin",
                "SYSTEMROOT": "C:\\Windows",
                "github_token": "secret",
                "pythonpath": "/tmp/python",
            }
        )

        assert env == {"AGENT_FLAG": "1"}


@pytest.mark.skipif(os.name == "nt", reason="process group behavior differs on Windows")
def test_terminate_process_group_kills_background_child(tmp_path: Path):
    marker = tmp_path / "child-ran"
    child_script = (
        f"import pathlib, time; time.sleep(0.4); pathlib.Path({str(marker)!r}).write_text('ran')"
    )
    parent_script = (
        "import subprocess, sys; "
        f"subprocess.Popen([{sys.executable!r}, '-c', {child_script!r}]); "
        "sys.exit(0)"
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            parent_script,
        ],
        **subprocess_group_kwargs(),
    )
    proc.wait(timeout=2)

    terminate_process_group(proc)
    time.sleep(0.6)

    assert not marker.exists()


@pytest.mark.skipif(os.name == "nt", reason="process group behavior differs on Windows")
def test_terminate_process_group_kills_sigterm_ignoring_child_after_parent_exits(tmp_path: Path):
    ready = tmp_path / "child-ready"
    marker = tmp_path / "child-ran"
    child_script = (
        "import pathlib, signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"pathlib.Path({str(ready)!r}).write_text('ready'); "
        "time.sleep(0.4); "
        f"pathlib.Path({str(marker)!r}).write_text('ran')"
    )
    parent_script = (
        "import subprocess, sys; "
        f"subprocess.Popen([{sys.executable!r}, '-c', {child_script!r}]); "
        "sys.exit(0)"
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            parent_script,
        ],
        **subprocess_group_kwargs(),
    )
    proc.wait(timeout=2)

    deadline = time.monotonic() + 2
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ready.exists()

    terminate_process_group(proc, timeout=0.1)
    time.sleep(0.6)

    assert not marker.exists()


def _spawn_child(child_code: str) -> subprocess.Popen:
    """Spawn a python child with the same pipe contract client.py uses."""
    return subprocess.Popen(
        [sys.executable, "-c", child_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
        **subprocess_group_kwargs(),
    )


def _cleanup_child(proc: subprocess.Popen) -> None:
    terminate_process_group(proc)
    for pipe in (proc.stdout, proc.stderr):
        if pipe is not None:
            pipe.close()


def _run_bounded(fn, *args, deadline: float = 3.0):
    """Run fn(*args) in a daemon thread behind a hard watchdog.

    The pre-fix select branch blocks without bound on partial-bytes shapes;
    without this harness a regression test would hang CI instead of failing.
    A watchdog trip is therefore a deterministic failure of the bound.
    """
    result: list = []

    def _target():
        try:
            result.append(fn(*args))
        except BaseException as exc:  # transported to the test thread
            result.append(exc)

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(deadline)
    if worker.is_alive():
        pytest.fail(
            f"{getattr(fn, '__name__', 'call')} still blocked after "
            f"{deadline}s watchdog (unbounded read)"
        )
    payload = result[0]
    if isinstance(payload, BaseException):
        raise payload
    return payload


class TestTimedReadlineThreadBranch:
    """Thread-branch coverage, forced everywhere so ubuntu CI exercises it too."""

    @pytest.fixture(autouse=True)
    def _force_thread_branch(self, monkeypatch):
        monkeypatch.setattr(registry_utils, "_TIMED_READ_USES_SELECT", False)

    def test_returns_line_within_timeout(self):
        proc = _spawn_child("print('hello', flush=True); import time; time.sleep(5)")
        try:
            assert timed_readline(proc.stdout, 5) == "hello\n"
        finally:
            _cleanup_child(proc)

    def test_timeout_returns_none_without_blocking_indefinitely(self):
        proc = _spawn_child("import time; time.sleep(5)")
        try:
            start = time.monotonic()
            assert timed_readline(proc.stdout, 0.5) is None
            elapsed = time.monotonic() - start
            assert elapsed < 3.0
        finally:
            _cleanup_child(proc)

    def test_eof_without_output_returns_none(self):
        proc = _spawn_child("pass")
        try:
            proc.wait(timeout=5)
            assert timed_readline(proc.stdout, 5) is None
        finally:
            _cleanup_child(proc)

    def test_line_buffered_before_eof_survives_immediate_exit(self):
        # Regression for the WinError 10038 card: the agent writes its
        # handshake and exits immediately; the first read must still return
        # the line and the second must return None without waiting out the
        # full timeout (sentinel re-queue after EOF).
        proc = _spawn_child('print(\'{"jsonrpc": "2.0"}\', flush=True)')
        try:
            assert timed_readline(proc.stdout, 5) == '{"jsonrpc": "2.0"}\n'

            start = time.monotonic()
            assert timed_readline(proc.stdout, 5) is None
            assert time.monotonic() - start < 1.0
        finally:
            _cleanup_child(proc)


class TestTimedReadThreadBranch:
    @pytest.fixture(autouse=True)
    def _force_thread_branch(self, monkeypatch):
        monkeypatch.setattr(registry_utils, "_TIMED_READ_USES_SELECT", False)

    def test_returns_chunk_then_eof(self):
        proc = _spawn_child("import sys; sys.stdout.write('chunk-data'); sys.stdout.flush()")
        try:
            assert timed_read(proc.stdout, 5) == "chunk-data"

            start = time.monotonic()
            assert timed_read(proc.stdout, 5) is None
            assert time.monotonic() - start < 1.0
        finally:
            _cleanup_child(proc)

    def test_timeout_returns_none(self):
        proc = _spawn_child("import time; time.sleep(5)")
        try:
            start = time.monotonic()
            assert timed_read(proc.stdout, 0.5) is None
            assert time.monotonic() - start < 3.0
        finally:
            _cleanup_child(proc)


@pytest.mark.skipif(os.name == "nt", reason="select() rejects pipes on Windows")
class TestTimedReadSelectBranch:
    """The POSIX production branch: select readiness + bounded raw reads."""

    def test_timed_readline_returns_line(self):
        proc = _spawn_child("print('hello', flush=True); import time; time.sleep(5)")
        try:
            assert timed_readline(proc.stdout, 5) == "hello\n"
        finally:
            _cleanup_child(proc)

    def test_timed_readline_timeout_returns_none(self):
        proc = _spawn_child("import time; time.sleep(5)")
        try:
            assert timed_readline(proc.stdout, 0.5) is None
        finally:
            _cleanup_child(proc)

    def test_timed_read_returns_chunk(self):
        proc = _spawn_child("import sys; sys.stdout.write('chunk-data'); sys.stdout.flush()")
        try:
            assert timed_read(proc.stdout, 5) == "chunk-data"
        finally:
            _cleanup_child(proc)

    def test_timed_read_partial_bytes_alive_child_returns_bounded(self):
        # CASE1 regression (the crush-acp ubuntu hang): a child that wrote
        # 0 < n < 8192 bytes and stays alive must not wedge the read. The
        # pre-fix buffered read(8192) blocks until EOF; the watchdog turns
        # that shape into a failure instead of a hung CI job.
        proc = _spawn_child(
            "import sys, time; sys.stdout.write('partial'); sys.stdout.flush(); time.sleep(5)"
        )
        try:
            start = time.monotonic()
            assert _run_bounded(timed_read, proc.stdout, 5) == "partial"
            assert time.monotonic() - start < 3.0
        finally:
            _cleanup_child(proc)

    def test_timed_readline_partial_line_no_newline_times_out_bounded(self):
        # CASE5 regression: select reports ready on any bytes, but a partial
        # line with no newline must never block past the timeout.
        proc = _spawn_child(
            "import sys, time; sys.stdout.write('{\"json\":'); sys.stdout.flush(); time.sleep(5)"
        )
        try:
            start = time.monotonic()
            assert _run_bounded(timed_readline, proc.stdout, 0.5) is None
            assert time.monotonic() - start < 3.0
        finally:
            _cleanup_child(proc)

    def test_timed_readline_two_lines_single_write_delivered_separately(self):
        # Parity guard: buffered readline() delivered a multi-line burst one
        # line at a time; the raw-read branch must stash post-newline bytes
        # and do the same.
        proc = _spawn_child(
            "import sys, time; sys.stdout.write('line1\\nline2\\n'); "
            "sys.stdout.flush(); time.sleep(5)"
        )
        try:
            assert _run_bounded(timed_readline, proc.stdout, 5) == "line1\n"
            assert _run_bounded(timed_readline, proc.stdout, 5) == "line2\n"
        finally:
            _cleanup_child(proc)

    def test_timed_readline_partial_line_then_eof_returns_tail(self):
        # EOF parity: a final partial line without a newline is still
        # returned, matching buffered readline() and the thread worker.
        proc = _spawn_child("import sys; sys.stdout.write('tail'); sys.stdout.flush()")
        try:
            proc.wait(timeout=5)
            assert _run_bounded(timed_readline, proc.stdout, 5) == "tail"
        finally:
            _cleanup_child(proc)

    def test_timed_readline_partial_bytes_stashed_across_timeout(self):
        # Client-level contract: bytes read before a timeout must survive to
        # the next call. Dropping them would decode a truncated fragment and
        # report a false ACP spec violation instead of completing the line.
        proc = _spawn_child(
            "import sys, time; "
            "sys.stdout.write('{\"json\":'); sys.stdout.flush(); "
            "time.sleep(1); "
            "sys.stdout.write('\"id\":1}\\n'); sys.stdout.flush(); "
            "time.sleep(5)"
        )
        try:
            assert _run_bounded(timed_readline, proc.stdout, 0.5) is None
            assert _run_bounded(timed_readline, proc.stdout, 5) == '{"json":"id":1}\n'
        finally:
            _cleanup_child(proc)
