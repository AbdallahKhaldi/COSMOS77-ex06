"""Gmail sender tests — fully mocked (no google libs, no network, no browser; rule 6)."""

from __future__ import annotations

import base64
from email import message_from_bytes

from cosmos77_ex06.report.gmail_sender import GmailSender, credentials_path
from cosmos77_ex06.shared.config import Config


class _Caught:
    """A fake Gmail service that records the send() arguments."""

    def __init__(self) -> None:
        self.args: dict = {}

    def users(self):  # noqa: D102
        return self

    def messages(self):  # noqa: D102
        return self

    def send(self, *, userId: str, body: dict):  # noqa: N803, D102
        self.args = {"userId": userId, "raw": body["raw"]}
        return self

    def execute(self):  # noqa: D102
        return {"id": "msg-1"}


class _Creds:
    def __init__(self, valid=True, expired=False, refresh_token=None) -> None:
        self.valid, self.expired, self.refresh_token = valid, expired, refresh_token
        self.refreshed = False

    def refresh(self, _request) -> None:
        self.refreshed = True
        self.valid = True

    def to_json(self) -> str:
        return '{"token": "fake"}'


def _sender(config: Config, svc: _Caught, **kw) -> GmailSender:
    return GmailSender(
        config,
        service_factory=lambda _creds: svc,
        creds_loader=kw.get("creds_loader", lambda _p, _s: _Creds(valid=True)),
        consent=kw.get("consent", lambda _p, _s: _Creds(valid=True)),
    )


def test_send_body_is_raw_json_and_userid_me(config: Config) -> None:
    """The email BODY is exactly the JSON string; userId='me'; recipient from config."""
    svc = _Caught()
    body = '{"group_name": "COSMOS77", "totals": {"cop": 20, "thief": 5}}'
    resp = _sender(config, svc).send(body)
    assert resp == {"id": "msg-1"}
    assert svc.args["userId"] == "me"
    mime = message_from_bytes(base64.urlsafe_b64decode(svc.args["raw"]))
    assert mime["To"] == "rmisegal+uoh26b@gmail.com"
    assert mime.get_payload(decode=True).decode("utf-8") == body  # JSON-only body, no prose


def test_valid_token_skips_consent_and_refresh(config: Config) -> None:
    """Valid stored creds are used as-is (no browser, no refresh, no token rewrite)."""
    consent_calls = []
    creds = _Creds(valid=True)
    _sender(
        config,
        _Caught(),
        creds_loader=lambda _p, _s: creds,
        consent=lambda *_: consent_calls.append(1) or creds,
    ).send("{}")
    assert consent_calls == [] and creds.refreshed is False


def test_expired_token_refreshes_without_consent(config: Config) -> None:
    """An expired token with a refresh token refreshes silently (no browser)."""
    creds = _Creds(valid=False, expired=True, refresh_token="r")
    consent_calls: list[int] = []
    svc = _Caught()
    GmailSender(
        config,
        service_factory=lambda _c: svc,
        creds_loader=lambda _p, _s: creds,
        consent=lambda *_: consent_calls.append(1) or creds,
    ).send("{}")
    assert creds.refreshed is True and consent_calls == []


def test_no_token_runs_consent_once(config: Config) -> None:
    """No stored token → the one-time consent runs and the result is persisted."""
    minted = _Creds(valid=True)
    calls: list[int] = []
    GmailSender(
        config,
        service_factory=lambda _c: _Caught(),
        creds_loader=lambda _p, _s: None,
        consent=lambda _p, _s: (calls.append(1), minted)[1],
    ).send("{}")
    assert calls == [1]
    token = config.config_dir.parent / "token.json"
    assert token.exists()  # creds persisted after mint


def test_credentials_path_is_repo_rooted_and_gitignored_name(config: Config) -> None:
    assert credentials_path(config).name == "credentials.json"


def test_to_override_beats_config_recipient(config: Config) -> None:
    """`--to` (a self-test recipient) overrides config report.to; default uses config."""
    assert GmailSender(config).to == "rmisegal+uoh26b@gmail.com"
    assert GmailSender(config, to="abdallahkh12@icloud.com").to == "abdallahkh12@icloud.com"
