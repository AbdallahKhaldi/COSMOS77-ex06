"""Gmail-API sender for the autonomous internal-game JSON report (E7, Phase 9).

The email BODY *is* the canonical report JSON — no prose, no HTML, no attachment
(spec §13 step 8). :class:`GmailSender` runs the OAuth Desktop flow
(``credentials.json`` -> ``token.json`` with auto-refresh), builds a plain-text
MIME message whose payload is the JSON string, base64**url**-encodes it, and calls
``service.users().messages().send(userId="me", body={"raw": raw})``.

Everything (recipient, scope, paths) is config-driven (rule 4 / E8); an optional
``to`` override lets you test-send to your own address without touching the
submission config. All ``google.*`` imports are LAZY + ``# pragma: no cover`` so
the suite needs no network/credentials; tests inject fake factory callables.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from cosmos77_ex06.shared.config import Config

#: The minimal sufficient OAuth scope: compose-and-send only (PRD §5.1).
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
#: Subject line is metadata, not body; the JSON-only constraint is about the body.
DEFAULT_SUBJECT = "COSMOS77-ex06 internal_game report"


class GmailSender:
    """Send ONE JSON-body email via the Gmail API (dependency-injectable for tests).

    ``to`` overrides the config recipient (handy for a self-test); the three factory
    callables let tests drive every branch without real OAuth, network, or a browser:
    ``service_factory(creds)`` returns a fake service; ``creds_loader(token, scope)``
    returns stored credentials (or ``None``); ``consent(creds_path, scope)`` returns
    freshly-authorized credentials. In production all default to the real google flow.
    """

    def __init__(
        self,
        config: Config,
        *,
        to: str | None = None,
        subject: str | None = None,
        service_factory: Callable[[Any], Any] | None = None,
        creds_loader: Callable[[Path, str], Any] | None = None,
        consent: Callable[[Path, str], Any] | None = None,
    ) -> None:
        self.config = config
        self._to_override = to
        self._subject_override = subject
        root = config.config_dir.parent
        self._credentials_path = root / str(
            config.get("report.credentials_file", "credentials.json")
        )
        self._token_path = root / str(config.get("report.token_file", "token.json"))
        self._scope = str(config.get("report.scope", GMAIL_SEND_SCOPE))
        self._service_factory = service_factory or self._real_service
        self._creds_loader = creds_loader or self._real_load_token
        self._consent = consent or self._real_consent

    @property
    def to(self) -> str:
        """The recipient: the ``to`` override if given, else config ``report.to``."""
        return str(self._to_override or self.config.get("report.to"))

    def _build_raw(self, body: str) -> str:
        """Wrap ``body`` (the canonical JSON) in a MIME text part, base64url-encoded.

        The JSON string itself is the message payload (no prose). UTF-8 charset
        preserves the Hebrew student names byte-for-byte (bonus byte-identity, E12).
        """
        mime = MIMEText(body, _charset="utf-8")
        mime["To"] = self.to
        mime["Subject"] = str(
            self._subject_override or self.config.get("report.subject", DEFAULT_SUBJECT)
        )
        return base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")

    def send(self, body: str) -> dict[str, Any]:
        """Send ``body`` (canonical JSON) as the email body; return the API response.

        Validation is the caller's responsibility (the SDK validates against the
        pydantic schema BEFORE calling this). The recipient is read from config.
        """
        raw = self._build_raw(body)
        service = self._service_factory(self._credentials())
        return service.users().messages().send(userId="me", body={"raw": raw}).execute()

    def _credentials(self) -> Any:
        """Return valid OAuth credentials: load token.json, refresh, or consent.

        Pure control flow (no google import): loads stored credentials, returns them
        if valid, refreshes (no browser) when expired with a refresh token, else runs
        the one-time consent. Persists the result to ``token.json`` after any mint.
        """
        creds = self._creds_loader(self._token_path, self._scope)
        if creds is not None and getattr(creds, "valid", False):
            return creds
        if (
            creds is not None
            and getattr(creds, "expired", False)
            and getattr(creds, "refresh_token", None)
        ):
            creds.refresh(self._request())
        else:
            creds = self._consent(self._credentials_path, self._scope)
        self._token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def _request(self) -> Any:
        """A google ``Request`` for token refresh (lazy import; real SDK only)."""
        from google.auth.transport.requests import Request  # pragma: no cover

        return Request()  # pragma: no cover

    def _real_service(self, creds: Any) -> Any:  # pragma: no cover - real SDK only
        """Build the live Gmail ``v1`` service (lazy import; no CI network)."""
        from googleapiclient.discovery import build

        return build("gmail", "v1", credentials=creds)

    def _real_load_token(self, token_path: Path, scope: str) -> Any:  # pragma: no cover
        """Load credentials from ``token.json`` (or ``None`` if absent); real SDK only."""
        from google.oauth2.credentials import Credentials

        if not token_path.exists():
            return None
        return Credentials.from_authorized_user_file(str(token_path), [scope])

    def _real_consent(self, credentials_path: Path, scope: str) -> Any:  # pragma: no cover
        """Run the one-time InstalledAppFlow consent (opens a browser); real SDK only."""
        from google_auth_oauthlib.flow import InstalledAppFlow

        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail OAuth client secrets not found: {credentials_path}. Create a "
                "Google Cloud OAuth *Desktop* client, enable the Gmail API, download the "
                "secrets, save them as credentials.json in the repo root, and add yourself "
                "as a Test user (see docs/prompts/009_phase9_report.md)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), [scope])
        return flow.run_local_server(port=0)


def credentials_path(config: Config) -> Path:
    """Repo-rooted path to the (gitignored) Gmail ``credentials.json``."""
    return config.config_dir.parent / str(config.get("report.credentials_file", "credentials.json"))
