"""Tests for Codespaces/Docker bootstrap import path."""

from pathlib import Path

from scripts import codespaces_bootstrap as bootstrap


def test_load_database_module():
    db = bootstrap._load_database_module()
    assert hasattr(db, "init_db")
    assert Path(db.__file__).name == "database.py"


def test_bootstrap_main_runs_init_db(monkeypatch):
    calls = []

    class FakeDB:
        def init_db(self):
            calls.append("init")

    monkeypatch.setattr(bootstrap.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(bootstrap, "_load_database_module", lambda: FakeDB())
    assert bootstrap.main() == 0
    assert calls == ["init"]
