"""
Email sending utility via smtplib — replaces PHPMailer/ttrssMailer.

Source: ttrss/classes/ttrssmailer.php:ttrssMailer (SMTP configuration and quickMail)
        ttrss/config.php (SMTP_* constants — SMTP_SERVER, SMTP_LOGIN, SMTP_PASSWORD,
                          SMTP_FROM_ADDRESS, SMTP_FROM_NAME, SMTP_SECURE)
Adapted: PHPMailer replaced by Python stdlib smtplib + email.mime (ADR-0002).
         PHP config constants (define()) replaced by os.environ lookups.
New: is_html flag controls Content-Type (PHPMailer used $this->IsHTML($altbody != '')).
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.


def send_mail(
    to_address: str,
    to_name: str,
    subject: str,
    body: str,
    is_html: bool = False,
) -> bool:
    """
    # Source: ttrss/classes/ttrssmailer.php:ttrssMailer::quickMail
    Send email via SMTP. Config from environment:
      SMTP_SERVER, SMTP_PORT (default 25), SMTP_LOGIN, SMTP_PASSWORD,
      SMTP_FROM_ADDRESS, SMTP_FROM_NAME, SMTP_SECURE (tls/ssl/"").
    Returns True on success, False on failure (logs error, does not raise).
    New: uses Python smtplib instead of PHPMailer.
    """
    # Source: ttrss/classes/ttrssmailer.php lines 15-16 — $this->From / $this->FromName
    from_address: str = os.environ.get("SMTP_FROM_ADDRESS", "")
    from_name: str = os.environ.get("SMTP_FROM_NAME", "")

    # Source: ttrss/classes/ttrssmailer.php lines 24-35 — SMTP_SERVER split on ':' for host/port
    smtp_server: str = os.environ.get("SMTP_SERVER", "")
    smtp_port: int = int(os.environ.get("SMTP_PORT", "25"))

    if smtp_server:
        # Source: ttrss/classes/ttrssmailer.php lines 25-31 — $pair = explode(":", SMTP_SERVER, 2)
        if ":" in smtp_server:
            host, port_str = smtp_server.rsplit(":", 1)
            try:
                smtp_port = int(port_str)
            except ValueError:
                pass  # keep SMTP_PORT env value
        else:
            host = smtp_server
    else:
        host = "localhost"

    # Source: ttrss/classes/ttrssmailer.php lines 38-43 — SMTP_LOGIN enables SMTPAuth
    smtp_login: str = os.environ.get("SMTP_LOGIN", "")
    smtp_password: str = os.environ.get("SMTP_PASSWORD", "")

    # Source: ttrss/classes/ttrssmailer.php line 44-45 — SMTP_SECURE ('tls', 'ssl', or '')
    smtp_secure: str = os.environ.get("SMTP_SECURE", "").lower()

    # Source: ttrss/classes/ttrssmailer.php line 18 — $this->CharSet = "UTF-8"
    # Build MIME message — HTML or plain text (controlled by is_html)
    # Source: ttrss/classes/ttrssmailer.php:quickMail — $this->IsHTML($altbody != '')
    if is_html:
        msg = MIMEMultipart("alternative")
        # New: provide a plain-text fallback for HTML digests (no PHP equivalent).
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))

    # Source: ttrss/classes/ttrssmailer.php:quickMail line 55 — $this->addAddress($toAddress, $toName)
    # RFC 2822 formatted To: header with display name
    if to_name:
        msg["To"] = f"{to_name} <{to_address}>"
    else:
        msg["To"] = to_address

    # Source: ttrss/classes/ttrssmailer.php lines 15-16 — From / FromName
    if from_name:
        msg["From"] = f"{from_name} <{from_address}>"
    else:
        msg["From"] = from_address

    # Source: ttrss/classes/ttrssmailer.php:quickMail line 56 — $this->Subject = $subject
    msg["Subject"] = subject

    try:
        # Source: ttrss/classes/ttrssmailer.php lines 24-45 — SMTP connection setup
        # ssl: connect with SSL from the start (smtplib.SMTP_SSL)
        # tls: connect plain then STARTTLS (smtplib.SMTP + starttls())
        # "": plain SMTP
        if smtp_secure == "ssl":
            # Source: ttrss/classes/ttrssmailer.php line 44 — SMTPSecure = 'ssl'
            conn: smtplib.SMTP = smtplib.SMTP_SSL(host, smtp_port, timeout=30)
        else:
            conn = smtplib.SMTP(host, smtp_port, timeout=30)
            if smtp_secure == "tls":
                # Source: ttrss/classes/ttrssmailer.php line 44 — SMTPSecure = 'tls'
                conn.starttls()

        with conn:
            if smtp_login:
                # Source: ttrss/classes/ttrssmailer.php lines 38-43 — SMTPAuth with Username/Password
                conn.login(smtp_login, smtp_password)
            conn.sendmail(from_address, [to_address], msg.as_string())

        logger.debug("send_mail: sent to %s subject=%r", to_address, subject)
        return True

    except Exception as exc:
        # Source: ttrss/classes/ttrssmailer.php — PHP: if (!$rc) _debug("ERROR: " . $mail->ErrorInfo)
        # Adapted: Python logs the exception rather than raising (caller checks return value).
        logger.error(
            "send_mail: failed to send to %s subject=%r: %s",
            to_address,
            subject,
            exc,
        )
        return False
