# Prompt log — Phase 9: Automated Gmail JSON report (E7)

**Goal.** The COP agent auto-sends ONE email whose body is the raw internal-game JSON (no prose)
to `rmisegal+uoh26b@gmail.com` at the end of a full game. Playbook §11, design in `docs/PRD_report.md`.
All Gmail I/O is mocked in the suite; the real send is a one-time user OAuth touchpoint.

## What was built
- `report/gmail_sender.py` — `GmailSender`: OAuth scope `https://www.googleapis.com/auth/gmail.send`;
  `credentials.json` → `token.json` via `InstalledAppFlow.run_local_server(port=0)` with
  auto-refresh; builds a `MIMEText` whose body IS the canonical JSON string; base64**url**-encodes it;
  `service.users().messages().send(userId="me", body={"raw": raw})`. All `google.*` imports are lazy
  + `# pragma: no cover` (CI needs no network/credentials). Recipient/scope/paths are config-driven.
- `report/dispatch.py` — `auto_send` (end-of-game email when `report.auto_send` is true; failures are
  recorded + swallowed so a missing `credentials.json` never crashes a run mid-pipeline, E5) and
  `send_latest` (the CLI `report --send` path: load the latest on-disk report, **validate against the
  pydantic schema BEFORE any send**, canonically serialize, email the JSON-only body).
- `report/output.py` (canonical serializer, from Phase 7) is reused so the emailed bytes match the
  saved `internal_game.json` exactly.
- `SDK.run_full_game` calls `dispatch.auto_send` when `report.auto_send` is true; `SDK.report(send=...)`
  drives `report --send`. Config gained `report.auto_send: false` (default OFF, safe when unconfigured).

## The exact send call shape
```python
mime = MIMEText(canonical_json, _charset="utf-8"); mime["To"] = to; mime["Subject"] = subject
raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
service.users().messages().send(userId="me", body={"raw": raw}).execute()
```

## One-time user setup (the Gmail touchpoint)
1. Google Cloud Console → **enable the Gmail API** for the project.
2. **Google Auth Platform** → External + Testing; under **Audience → Test users** add your own Gmail.
3. **Clients → Create client → Desktop app** → Download JSON → rename to `credentials.json` → place in
   the repo root (it is gitignored, never committed).
4. First `uv run cosmos77-pursuit report --send` opens the browser consent (click through the
   "app isn't verified" warning — normal in Testing mode), writes `token.json`, and sends. Later sends
   are silent (auto-refresh). If you ever change scopes, delete `token.json` and re-consent.

## Fixes after a mid-build interruption (the worker's connection dropped)
- `sdk.py` had grown to 161 lines → condensed docstrings back under the 150-line cap.
- `test_sdk.py` still listed `report()` as an "unimplemented stage" → replaced with a real test that
  `report()` raises `FileNotFoundError` when no report exists on disk.

## Verification
ruff / format / line-cap clean; `pytest -m 'not live'` green (Gmail fully mocked — body-is-JSON,
base64url, `userId="me"`, recipient, token-refresh all asserted). `credentials.json`/`token.json`
remain gitignored. No live Gmail call in the suite.
