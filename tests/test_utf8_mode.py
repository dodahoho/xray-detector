"""UTF-8-läge för hela appen (TASK-173, TASK-176).

Utan UTF-8-läget läser tredjeparten klassnamn som cp1252, och då blir
"löpare" till "lÃ¶pare" i de tränade vikterna. Flaggan läses när tolken
startar, så appen sätter den i miljön och startar om sig själv en gång när
läget är av. Omstarten väntar på den nya processen, så terminalen stannar
kvar hos appen och kommandoprompten kommer tillbaka när appen stängs.
"""

import os
import subprocess
import sys

from PySide6.QtCore import QProcess

from xray_detector.app import RESTARTED_ENV, UTF8_ENV, _ensure_utf8_mode


def _completed(args, code=0):
    return subprocess.CompletedProcess(args, code)


def test_the_flag_is_set_for_child_processes(monkeypatch):
    monkeypatch.delenv(UTF8_ENV, raising=False)

    _ensure_utf8_mode(utf8_mode=True)

    assert os.environ[UTF8_ENV] == "1"


def test_no_restart_when_the_process_already_reads_utf8(monkeypatch):
    runs = []
    monkeypatch.setattr(subprocess, "run", lambda args: runs.append(args))

    _ensure_utf8_mode(utf8_mode=True)

    assert runs == []


def test_the_restart_reuses_the_command_line(monkeypatch):
    monkeypatch.delenv(RESTARTED_ENV, raising=False)
    runs = []
    exits = []

    def fake_run(args):
        runs.append(args)
        return _completed(args)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "exit", exits.append)

    _ensure_utf8_mode(utf8_mode=False)

    assert runs == [[sys.executable, *sys.orig_argv[1:]]]
    assert exits == [0]


def test_the_restart_returns_the_childs_exit_code(monkeypatch):
    monkeypatch.delenv(RESTARTED_ENV, raising=False)
    exits = []
    monkeypatch.setattr(subprocess, "run", lambda args: _completed(args, 3))
    monkeypatch.setattr(sys, "exit", exits.append)

    _ensure_utf8_mode(utf8_mode=False)

    assert exits == [3]


def test_the_restart_happens_at_most_once(monkeypatch):
    """En kommandorad med -X utf8=0 slår miljövariabeln och får inte loopa."""
    monkeypatch.setenv(RESTARTED_ENV, "1")
    runs = []
    monkeypatch.setattr(subprocess, "run", lambda args: runs.append(args))

    _ensure_utf8_mode(utf8_mode=False)

    assert runs == []


def test_a_child_process_inherits_the_flag(qapp, monkeypatch):
    """Träningen startas som en QProcess och ärver appens miljö."""
    monkeypatch.setenv(UTF8_ENV, "1")
    process = QProcess()
    process.start(sys.executable, ["-c", "import sys; print(sys.flags.utf8_mode)"])

    assert process.waitForFinished(30000)
    assert process.readAllStandardOutput().data().decode().strip() == "1"
