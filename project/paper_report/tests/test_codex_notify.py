from __future__ import annotations

import subprocess

from paper_report.codex_notify import CodexGmailNotifier


def test_codex_gmail_notifier_invokes_codex_with_recipient_and_error_reason(tmp_path, monkeypatch):
    monkeypatch.setattr("paper_report.codex_notify.shutil.which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    calls = []

    def runner(command, cwd, timeout):
        calls.append((command, cwd, timeout))
        return subprocess.CompletedProcess(command, 0, stdout='{"success": true, "email_sent": true}', stderr="")

    notifier = CodexGmailNotifier(recipient="openclaw572@gmail.com", workdir=tmp_path / "codex-work", runner=runner)
    result = notifier.send_pipeline_result({"ok": False, "error": "YouTube upload failed", "cleanup_done": False})

    assert result.ok
    assert result.recipient == "openclaw572@gmail.com"
    assert (tmp_path / "codex-work" / ".git").exists()
    prompt = calls[0][0][-1]
    assert "openclaw572@gmail.com" in prompt
    assert "YouTube upload failed" in prompt
    assert "實際傳送 Gmail" in prompt


def test_codex_gmail_notifier_reports_missing_codex(tmp_path, monkeypatch):
    monkeypatch.setattr("paper_report.codex_notify.shutil.which", lambda name: None)

    notifier = CodexGmailNotifier(workdir=tmp_path / "codex-work")
    result = notifier.send_pipeline_result({"ok": True})

    assert not result.ok
    assert "codex CLI not found" in result.error
