import json
from email.utils import parseaddr
from pathlib import Path

import pytest

from app.services.mail_service import SmtpMailSender


@pytest.fixture
def smtp_capture(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.connection = (host, port, timeout)
            self.messages = []
            self.login_calls = []
            self.tls = False

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self, *, context):
            assert context is not None
            self.tls = True

        def login(self, username, password):
            self.login_calls.append((username, password))

        def send_message(self, message):
            self.messages.append(message)

    capture = FakeSMTP("smtp.test", 587, 10)

    def connect(host, port, timeout):
        assert (host, port, timeout) == capture.connection
        return capture

    monkeypatch.setattr("app.services.mail_service.smtplib.SMTP", connect)
    return capture


def sender_config():
    return {
        "host": "smtp.test", "port": 587, "use_tls": True,
        "username": "owner@bearahandllc.com", "password": "synthetic-mail-secret",
        "from_email": "owner@bearahandllc.com", "from_name": "Bear A Hand Sports Support",
    }


@pytest.mark.parametrize("method,path", [
    ("send_email_verification", "/verify-email?token="),
    ("send_password_reset", "/reset-password?token="),
    ("send_recovery_email_verification", None),
    ("send_forgot_email_code", None),
])
def test_all_customer_messages_use_named_public_sender(smtp_capture, caplog, method, path):
    sender = SmtpMailSender(sender_config(), "https://bearahandsports.com")
    recipient = "synthetic-recipient@example.test"
    token = "synthetic-private-token"
    getattr(sender, method)(recipient, token)
    assert len(smtp_capture.messages) == 1
    message = smtp_capture.messages[0]
    assert str(message["From"]) == "Bear A Hand Sports Support <owner@bearahandllc.com>"
    assert parseaddr(str(message["From"])) == ("Bear A Hand Sports Support", "owner@bearahandllc.com")
    assert str(message["To"]) == recipient
    assert smtp_capture.tls
    assert smtp_capture.login_calls == [("owner@bearahandllc.com", "synthetic-mail-secret")]
    if path:
        assert "https://bearahandsports.com" + path + token in message.get_content()
    assert token not in str(message["From"])
    assert "synthetic-mail-secret" not in message.as_string()
    assert token not in caplog.text
    assert recipient not in caplog.text
    assert "synthetic-mail-secret" not in caplog.text


def test_existing_address_only_sender_configuration_is_preserved(smtp_capture):
    config = sender_config()
    config.pop("from_name")
    SmtpMailSender(config).send_email_verification("synthetic@example.test", "opaque")
    assert str(smtp_capture.messages[0]["From"]) == "owner@bearahandllc.com"


def test_sender_name_cannot_inject_headers(smtp_capture):
    config = sender_config()
    config["from_name"] = "Support\r\nBcc: injected@example.test"
    with pytest.raises(RuntimeError, match="sender name is invalid"):
        SmtpMailSender(config).send_email_verification("synthetic@example.test", "opaque")
    assert not smtp_capture.messages
    assert not smtp_capture.login_calls


@pytest.mark.parametrize("field,value", [
    ("host", ""), ("from_email", ""), ("from_email", "Support <owner@bearahandllc.com>"),
])
def test_unconfigured_or_formatted_sender_fails_before_delivery(smtp_capture, field, value):
    config = sender_config()
    config[field] = value
    with pytest.raises(RuntimeError, match="not configured"):
        SmtpMailSender(config).send_password_reset("synthetic@example.test", "opaque")
    assert not smtp_capture.messages


@pytest.mark.parametrize("relative", [
    (".env.production.example",),
    ("backend", ".env.example"),
    ("backend", ".env.production.example"),
])
def test_environment_examples_use_intended_identity_without_credentials(relative):
    root = Path(__file__).parents[2]
    lines = root.joinpath(*relative).read_text().splitlines()
    value = next(line.split("=", 1)[1] for line in lines if line.startswith("SMTP_SETTINGS="))
    config = json.loads(value)
    assert config["from_email"] == config["username"] == "owner@bearahandllc.com"
    assert config["from_name"] == "Bear A Hand Sports Support"
    assert config["use_tls"] is True
    assert config["password"] in {"YOUR_PASSWORD", "replace-with-smtp-password"}
