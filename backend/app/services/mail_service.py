from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Protocol
from urllib.parse import urlencode

from app.core.config import settings


class MailSender(Protocol):
    def send_password_reset(self, recipient: str, token: str) -> None: ...

    def send_recovery_email_verification(self, recipient: str, code: str) -> None: ...

    def send_forgot_email_code(self, recipient: str, code: str) -> None: ...


class SmtpMailSender:
    def __init__(
        self,
        smtp_settings: dict[str, Any] | None = None,
        frontend_url: str | None = None,
    ) -> None:
        self.smtp_settings = smtp_settings if smtp_settings is not None else settings.SMTP_SETTINGS
        self.frontend_url = (frontend_url or settings.FRONTEND_URL).rstrip("/")

    def send_password_reset(self, recipient: str, token: str) -> None:
        host = str(self.smtp_settings.get("host", "")).strip()
        from_email = str(self.smtp_settings.get("from_email", "")).strip()
        if not host or not from_email or "<" in host or "<" in from_email:
            raise RuntimeError("SMTP delivery is not configured")

        reset_url = f"{self.frontend_url}/reset-password?{urlencode({'token': token})}"
        message = EmailMessage()
        message["Subject"] = "Reset your Golden Key password"
        message["From"] = from_email
        message["To"] = recipient
        message.set_content(
            "A password reset was requested for your Golden Key account.\n\n"
            f"Reset your password: {reset_url}\n\n"
            "This link expires in 20 minutes. If you did not request this, ignore this email."
        )

        self._send(message)

    def send_recovery_email_verification(self, recipient: str, code: str) -> None:
        message = self._message(
            recipient,
            "Verify your Golden Key recovery email",
            "Use this code to verify your Golden Key recovery email:\n\n"
            f"{code}\n\n"
            "This code expires in 10 minutes. If you did not request this, ignore this email.",
        )
        self._send(message)

    def send_forgot_email_code(self, recipient: str, code: str) -> None:
        message = self._message(
            recipient,
            "Your Golden Key account recovery code",
            "Use this code to recover your Golden Key sign-in email:\n\n"
            f"{code}\n\n"
            "This code expires in 10 minutes. If you did not request this, ignore this email.",
        )
        self._send(message)

    def _message(self, recipient: str, subject: str, body: str) -> EmailMessage:
        host = str(self.smtp_settings.get("host", "")).strip()
        from_email = str(self.smtp_settings.get("from_email", "")).strip()
        if not host or not from_email or "<" in host or "<" in from_email:
            raise RuntimeError("SMTP delivery is not configured")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = recipient
        message.set_content(body)
        return message

    def _send(self, message: EmailMessage) -> None:
        host = str(self.smtp_settings.get("host", "")).strip()
        from_email = str(self.smtp_settings.get("from_email", "")).strip()
        if not host or not from_email or "<" in host or "<" in from_email:
            raise RuntimeError("SMTP delivery is not configured")
        port = int(self.smtp_settings.get("port", 587))
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if bool(self.smtp_settings.get("use_tls", True)):
                smtp.starttls(context=ssl.create_default_context())
            username = str(self.smtp_settings.get("username", ""))
            password = str(self.smtp_settings.get("password", ""))
            if username:
                smtp.login(username, password)
            smtp.send_message(message)