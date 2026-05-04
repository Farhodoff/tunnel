"""
Tests for CLI entry points
"""

import sys
import pytest

import tunnel.cli as cli


def test_main_without_args_exits(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tunnel.cli"])
    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    assert "Usage: python -m tunnel.cli [server|client]" in capsys.readouterr().out


def test_main_unknown_command_exits(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tunnel.cli", "unknown"])
    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Unknown command: unknown" in output
    assert "Usage: python -m tunnel.cli [server|client]" in output


def test_main_dispatches_server(monkeypatch):
    called = {"server": False}

    def fake_run_server():
        called["server"] = True

    monkeypatch.setattr(cli, "run_server", fake_run_server)
    monkeypatch.setattr(sys, "argv", ["tunnel.cli", "server"])

    cli.main()

    assert called["server"] is True


def test_main_dispatches_client(monkeypatch):
    called = {"client": False}

    def fake_run_client():
        called["client"] = True

    monkeypatch.setattr(cli, "run_client", fake_run_client)
    monkeypatch.setattr(sys, "argv", ["tunnel.cli", "client"])

    cli.main()

    assert called["client"] is True
