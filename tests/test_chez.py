import os
import tempfile
from pathlib import Path
import subprocess
import sys
import pytest

# Import commands from alias.py as module
import sys
from pathlib import Path as _P
# ensure repo root is importable
sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
from alias import chezadd_cmd, chezcrypt_cmd


def make_temp_files(tmp_path, names):
    d = tmp_path / "src"
    d.mkdir()
    paths = []
    for n in names:
        p = d / n
        p.write_text(f"content {n}")
        paths.append(str(p))
    return str(d), paths


class DummyCompleted:
    def __init__(self, stdout=""):
        self.stdout = stdout


def test_chezadd_dry_run(monkeypatch, tmp_path, capsys):
    # create temp dir with files
    d, files = make_temp_files(tmp_path, ["a.txt", "b.md"]) 

    # monkeypatch _run to run the find command helper as real but not run chezmoi
    def fake_run(cmd, **kw):
        if cmd[0] == "find":
            # emulate find -print0 output
            out = "\x00".join(files) + "\x00"
            return DummyCompleted(stdout=out)
        raise RuntimeError("Unexpected command")

    monkeypatch.setattr(sys.modules['alias'], '_run', fake_run)

    # call chezadd_cmd in dry-run mode
    chezadd_cmd(dry_run=True, targets=[d])

    captured = capsys.readouterr()
    assert "chezmoi add" in captured.out


def test_chezcrypt_dry_run(monkeypatch, tmp_path, capsys):
    d, files = make_temp_files(tmp_path, ["x.txt", "y.md"]) 

    def fake_run(cmd, **kw):
        if cmd[0] == "find":
            out = "\x00".join(files) + "\x00"
            return DummyCompleted(stdout=out)
        raise RuntimeError("Unexpected command")

    monkeypatch.setattr(sys.modules['alias'], '_run', fake_run)

    chezcrypt_cmd(dry_run=True, targets=[d])
    captured = capsys.readouterr()
    assert "chezmoi add --encrypt" in captured.out
