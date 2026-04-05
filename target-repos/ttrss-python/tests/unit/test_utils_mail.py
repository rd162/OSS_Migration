"""Unit tests for ttrss/utils/mail.py — send_mail() SMTP wrapper.

All SMTP network calls are patched via unittest.mock so no real network is
required.  Each test cites its PHP source in the docstring per project convention.

PHP source file: ttrss/classes/ttrssmailer.php
"""
from __future__ import annotations

import smtplib
from email import message_from_string
from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.utils.mail import send_mail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_smtp_mock(conn_class: str = "smtplib.SMTP") -> tuple[MagicMock, MagicMock]:
    """Return (patcher_mock, conn_instance_mock) with context-manager support."""
    conn_mock = MagicMock(spec=smtplib.SMTP)
    # Support "with conn:" usage
    conn_mock.__enter__ = lambda s: s
    conn_mock.__exit__ = MagicMock(return_value=False)
    return conn_mock


# ---------------------------------------------------------------------------
# 1. Successful send returns True
# ---------------------------------------------------------------------------


def test_send_mail_success_returns_true(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer::quickMail line 59
    PHP:    $rc = $this->send(); return $rc;
    Assert: send_mail() returns True when SMTP.sendmail() does not raise.
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    conn_mock = _make_smtp_mock()
    with patch("smtplib.SMTP", return_value=conn_mock) as smtp_cls:
        result = send_mail("to@example.com", "Recipient", "Hello", "Body text")

    assert result is True
    smtp_cls.assert_called_once_with("mail.example.com", 25, timeout=30)
    conn_mock.sendmail.assert_called_once()


# ---------------------------------------------------------------------------
# 2. SMTP connection error → False, no exception propagated
# ---------------------------------------------------------------------------


def test_send_mail_smtp_error_returns_false(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer::quickMail lines 59-63
    PHP:    if (!$rc) _debug("ERROR: " . $mail->ErrorInfo);
    Assert: send_mail() catches SMTPException and returns False without raising.
    """
    monkeypatch.setenv("SMTP_SERVER", "bad-host.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("conn refused")):
        result = send_mail("to@example.com", "Recipient", "Subj", "Body")

    assert result is False


# ---------------------------------------------------------------------------
# 3. is_html=True → multipart/alternative with text part
# ---------------------------------------------------------------------------


def test_send_mail_html_creates_multipart_alternative(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer::quickMail line 58
    PHP:    $this->IsHTML($altbody != '');
    Assert: When is_html=True, the MIME message is multipart/alternative and
            contains at least one text/plain part (plain-text fallback).
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    captured: list[str] = []

    conn_mock = _make_smtp_mock()

    def capture_sendmail(from_addr, to_addrs, msg_str):
        captured.append(msg_str)

    conn_mock.sendmail.side_effect = capture_sendmail

    with patch("smtplib.SMTP", return_value=conn_mock):
        result = send_mail("to@example.com", "Bob", "Subj", "<b>Hi</b>", is_html=True)

    assert result is True
    assert len(captured) == 1
    msg = message_from_string(captured[0])
    assert msg.get_content_type() == "multipart/alternative"
    # Must contain a plain-text part
    content_types = [part.get_content_type() for part in msg.walk()]
    assert "text/plain" in content_types


# ---------------------------------------------------------------------------
# 4. is_html=False → plain text message (not multipart/alternative)
# ---------------------------------------------------------------------------


def test_send_mail_plain_text_content_type(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer::quickMail line 58
    PHP:    $this->IsHTML($altbody != '');  // False when no altbody
    Assert: When is_html=False, MIME message is NOT multipart/alternative;
            body is delivered as text/plain.
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    captured: list[str] = []

    conn_mock = _make_smtp_mock()
    conn_mock.sendmail.side_effect = lambda f, t, m: captured.append(m)

    with patch("smtplib.SMTP", return_value=conn_mock):
        result = send_mail("to@example.com", "Bob", "Subj", "Plain text", is_html=False)

    assert result is True
    msg = message_from_string(captured[0])
    assert msg.get_content_type() != "multipart/alternative"
    content_types = [part.get_content_type() for part in msg.walk()]
    assert "text/plain" in content_types


# ---------------------------------------------------------------------------
# 5. SMTP_LOGIN set → conn.login() called with credentials
# ---------------------------------------------------------------------------


def test_send_mail_login_called_when_smtp_login_set(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer.__construct__ lines 39-43
    PHP:    if (SMTP_LOGIN) { $this->SMTPAuth = true; $this->Username = SMTP_LOGIN; ... }
    Assert: conn.login(SMTP_LOGIN, SMTP_PASSWORD) is called exactly once.
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.setenv("SMTP_LOGIN", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "s3cr3t")
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    conn_mock = _make_smtp_mock()

    with patch("smtplib.SMTP", return_value=conn_mock):
        result = send_mail("to@example.com", "Recipient", "Subj", "Body")

    assert result is True
    conn_mock.login.assert_called_once_with("user@example.com", "s3cr3t")


# ---------------------------------------------------------------------------
# 6. SMTP_LOGIN empty → login NOT called
# ---------------------------------------------------------------------------


def test_send_mail_login_not_called_when_smtp_login_empty(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer.__construct__ line 39
    PHP:    if (SMTP_LOGIN) { ... }  // falsy SMTP_LOGIN skips auth block
    Assert: conn.login() is never called when SMTP_LOGIN is absent/empty.
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    conn_mock = _make_smtp_mock()

    with patch("smtplib.SMTP", return_value=conn_mock):
        result = send_mail("to@example.com", "Recipient", "Subj", "Body")

    assert result is True
    conn_mock.login.assert_not_called()


# ---------------------------------------------------------------------------
# 7. SMTP_FROM_NAME set → From header contains the display name
# ---------------------------------------------------------------------------


def test_send_mail_from_name_in_header(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php lines 15-16
    PHP:    public $From = SMTP_FROM_ADDRESS; public $FromName = SMTP_FROM_NAME;
    Assert: When SMTP_FROM_NAME is set, the From: header is "Name <addr>".
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "noreply@example.com")
    monkeypatch.setenv("SMTP_FROM_NAME", "TT-RSS")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    captured: list[str] = []
    conn_mock = _make_smtp_mock()
    conn_mock.sendmail.side_effect = lambda f, t, m: captured.append(m)

    with patch("smtplib.SMTP", return_value=conn_mock):
        send_mail("to@example.com", "", "Subj", "Body")

    msg = message_from_string(captured[0])
    assert "TT-RSS" in msg["From"]
    assert "noreply@example.com" in msg["From"]


# ---------------------------------------------------------------------------
# 8. to_name set → To header contains the display name
# ---------------------------------------------------------------------------


def test_send_mail_to_name_in_header(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer::quickMail line 55
    PHP:    $this->addAddress($toAddress, $toName);
    Assert: When to_name is provided, the To: header is "Name <addr>".
    """
    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_FROM_NAME", raising=False)
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    captured: list[str] = []
    conn_mock = _make_smtp_mock()
    conn_mock.sendmail.side_effect = lambda f, t, m: captured.append(m)

    with patch("smtplib.SMTP", return_value=conn_mock):
        send_mail("alice@example.com", "Alice Smith", "Subj", "Body")

    msg = message_from_string(captured[0])
    assert "Alice Smith" in msg["To"]
    assert "alice@example.com" in msg["To"]


# ---------------------------------------------------------------------------
# 9. SMTP_SERVER with embedded port → connects to correct host and port
# ---------------------------------------------------------------------------


def test_send_mail_smtp_server_with_port(monkeypatch):
    """
    Source: ttrss/classes/ttrssmailer.php:ttrssMailer.__construct__ lines 25-31
    PHP:    $pair = explode(":", SMTP_SERVER, 2); $this->Host = $pair[0]; $this->Port = $pair[1];
    Assert: When SMTP_SERVER is "host:587", SMTP is instantiated with host="host", port=587.
    """
    monkeypatch.setenv("SMTP_SERVER", "smtp.mailprovider.com:587")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "from@example.com")
    monkeypatch.delenv("SMTP_LOGIN", raising=False)
    monkeypatch.delenv("SMTP_SECURE", raising=False)

    conn_mock = _make_smtp_mock()

    with patch("smtplib.SMTP", return_value=conn_mock) as smtp_cls:
        send_mail("to@example.com", "", "Subj", "Body")

    smtp_cls.assert_called_once_with("smtp.mailprovider.com", 587, timeout=30)
