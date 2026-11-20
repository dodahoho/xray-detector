"""UTF-8-läge för hela appen (TASK-173).

Utan UTF-8-läget läser tredjeparten klassnamn som cp1252, och då blir
"löpare" till "lÃ¶pare" i de tränade vikterna. Flaggan läses när tolken
startar, så appen sätter den i miljön och startar om sig själv en gång när
läget är av.
"""

import os
import sys

from PySide6.QtCore import QProcess

from xray_detector.app import RESTARTED_ENV, UTF8_ENV, _ensure_utf8_mode


def test_the_flag_is_set_for_child_processes(monkeypatch):
    monkeypatch.delenv(UTF8_ENV, raising=False)

    _ensure_utf8_mode(utf8_mode=True)

    assert os.environ[UTF8_ENV] == "1"


def test_no_restart_when_the_process_already_reads_utf8(monkeypatch):
    restarts = []
    monkeypatch.setattr(os, "execv", lambda *args: restarts.append(args))

    _ensure_utf8_mode(utf8_mode=True)

    assert restarts == []


def test_the_restart_reuses_the_command_line(monkeypatch):
    monkeypatch.delenv(RESTARTED_ENV, raising=False)
    restarts = []
    monkeypatch.setattr(os, "execv", lambda *args: restarts.append(args))

    _ensure_utf8_mode(utf8_mode=False)

    assert restarts == [(sys.executable, [sys.executable, *sys.orig_argv[1:]])]


def test_the_restart_happens_at_most_once(monkeypatch):
    """En kommandorad med -X utf8=0 slår miljövariabeln och får inte loopa."""
    monkeypatch.setenv(RESTARTED_ENV, "1")
    restarts = []
    monkeypatch.setattr(os, "execv", lambda *args: restarts.append(args))

    _ensure_utf8_mode(utf8_mode=False)

    assert restarts == []


def test_a_child_process_inherits_the_flag(qapp, monkeypatch):
    """Träningen startas som en QProcess och ärver appens miljö."""
    monkeypatch.setenv(UTF8_ENV, "1")
    process = QProcess()
    process.start(sys.executable, ["-c", "import sys; print(sys.flags.utf8_mode)"])

    assert process.waitForFinished(30000)
    assert process.readAllStandardOutput().data().decode().strip() == "1"
