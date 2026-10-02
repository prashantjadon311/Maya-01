import os
from pathlib import Path
import tomllib
import psutil
import pytest

def test_daemon_lifecycle():
    """Verify that Project H daemon can initialize and shut down cleanly."""
    from app.main import Daemon

    daemon = Daemon()
    assert not daemon.is_running
    daemon.start()
    assert daemon.is_running
    daemon.stop()
    assert not daemon.is_running


def test_baseline_process_rss():
    """Measure baseline process RSS using psutil."""
    process = psutil.Process(os.getpid())
    rss_bytes = process.memory_info().rss
    rss_mib = rss_bytes / (1024 * 1024)

    # Sanity check: non-zero, realistic process memory
    assert rss_bytes > 0
    assert rss_mib < 300.0, f"Empty harness exceeds 300 MiB limit: {rss_mib:.2f} MiB"


def test_config_fixture_exists():
    """Verify that tests/fixtures/config.example.toml exists and is valid TOML."""
    fixture_path = Path(__file__).parent / "fixtures" / "config.example.toml"
    assert fixture_path.is_file(), f"Missing config fixture at {fixture_path}"

    with open(fixture_path, "rb") as f:
        data = tomllib.load(f)

    assert isinstance(data, dict)
    assert len(data) > 0


def test_no_credentials_required(monkeypatch):
    """Verify repository harness runs without NVIDIA or other external API credentials."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from app.main import Daemon

    daemon = Daemon()
    daemon.start()
    assert daemon.is_running
    daemon.stop()
    assert not daemon.is_running
