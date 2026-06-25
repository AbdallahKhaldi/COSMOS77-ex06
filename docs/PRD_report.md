# PRD — Automated JSON Report Builder + Gmail-API Sender

> **Module:** `src/cosmos77_ex06/report/`
> **Acceptance criteria covered:** **E7** (automated Gmail JSON report) and **E13** (Technical-Loss handling). Supports **E12** (the bonus) through the shared canonical serializer.
> **Spec anchors:** §9.1 (internal-game JSON schema), §13 step 8 (the autonomous send), Dr. Segal's *Google API setup guide* (OAuth Desktop client).
> **Architecture rule (graded):** No LLM and no game-truth lives here. This module is a pure, deterministic data-and-transport layer that the **orchestrator** invokes; it sits on the **MCP-Client side** of the Server/Client separation. The MCP servers never touch reporting.

---

## 1. Purpose and scope

At the end of a full game — exactly **6 valid sub-games** of at most **25 moves** each, with the thief moving first and the cop allowed up to 5 cop-only impassable barriers — the **Cop agent autonomously triggers a single email**. The email's body **is** the internal-game result JSON (no prose, no subject-line summary in the body, no attachment): a machine-readable record of who won each sub-game and the cumulative `cop`/`thief` totals under the scoring table (`cop_win` 20 / `thief_loss` 5; `thief_win` 10 / `cop_loss` 5).

This module has two cleanly separated responsibilities, each in its own ≤150-line file (rule 1):

1. **`report/output.py`** — assemble and **canonically serialize** the internal-game JSON from the final `GameState`/totals.
2. **`report/gmail_sender.py`** — authenticate via OAuth Desktop flow and send the raw JSON through the Gmail API.
3. **`report/schema.py`** — pydantic models for the internal-game and bonus JSON; validate **before** any send.

The build of the JSON is decoupled from its transport: the builder can emit a report to `reports/internal_game.json` for inspection/tests without ever touching the network, and the sender can be exercised against a mocked `googleapiclient`. This is what lets rule 6 (mock *all* network/Gmail I/O in the suite) hold while the real send is a one-time manual verification.

Why "automated" is load-bearing: **E5** demands a fully autonomous pipeline — `init → 6 valid sub-games → report` with zero manual intervention. The report is the terminal step of that pipeline. If a human had to click "send," the autonomy criterion would fail. So the orchestrator's runner calls `SDK.run_full_game()`, and the Cop agent's end-of-game hook invokes `build → validate → send` without a prompt.

---

## 2. The internal-game JSON schema (§9.1)

The report is a single JSON object with this exact key set:

| Key | Type | Source | Notes |
|---|---|---|---|
| `group_name` | string | `config.group.name` | `"COSMOS77"` |
| `students` | list of objects | config / roster | each `{id, name_en, name_he}` |
| `github_repo` | string | `config.group.github_repo` | the public repo URL |
| `cop_mcp_url` | string | `config.mcp.cop_url` | the **cloud** URL at submission (E6) |
| `thief_mcp_url` | string | `config.mcp.thief_url` | the **cloud** URL at submission |
| `timezone` | string | `config.report.timezone` | `"Asia/Jerusalem"` |
| `sub_games` | list of objects | the engine transcript | one entry per *valid* sub-game (see §2.1) |
| `totals` | object | accumulated scoring | `{cop: <int>, thief: <int>}` |

Everything is **config-driven** (rule 4 / E8): no field is literal in code. `report.to` (`rmisegal+uoh26b@gmail.com`) and `report.timezone` come from `config/config.yaml`; URLs and group metadata come from the same file. When the servers are deployed to public HTTPS URLs (Phase 8), the cop/thief URLs in the report automatically reflect the cloud endpoints because they are read from config, not hardcoded.

### 2.1 `sub_games[]` element

Each entry summarizes one *valid* (non-voided) sub-game. A representative shape:

```json
{
  "index": 1,
  "winner": "cop",
  "moves": 14,
  "capture": true,
  "cop_score": 20,
  "thief_score": 5
}
```

- `index` is 1-based and contiguous over the 6 valid sub-games (a voided Technical-Loss sub-game does **not** consume an index — see §6).
- `winner ∈ {"cop", "thief"}`; `capture` is `true` when the cop landed on the thief's cell, `false` when the thief survived the move limit.
- Per-sub-game scores apply the scoring table; `totals.cop = Σ cop_score`, `totals.thief = Σ thief_score`.

The transcript itself (every free-natural-language message and tool call) is logged separately for the README/CLI evidence (E10/E11) and is **not** part of the emailed report — the email is the compact, agreed result record so a partner group can reproduce it byte-for-byte.

---

## 3. The canonical serializer (determinism is non-negotiable)

`output.py` exposes a single canonical serialization function (`canonical_json`) used by **both** the internal-game report (Phase 9) and the `bonus_game` report (Phase 11). Determinism here is what makes the **bonus** payable: §9.2 requires that **both groups email a byte-identical report**; any mismatch scores **0 for both** groups. Two independently-run Python processes, possibly on different machines/OSes, must emit identical bytes for the same logical result.

Canonical rules:

- **`sort_keys=True`** — keys serialized in a fixed, lexicographic order regardless of dict insertion order.
- **Fixed separators** — `separators=(",", ":")` (no incidental whitespace) *or* a fixed `indent=2`; pick one and apply it everywhere (we use a single fixed formatting so the bytes are stable). The choice must be identical on both sides of the bonus.
- **UTF-8, `ensure_ascii=False`** — Hebrew student names (`עבדאללה`, `תסנים`) serialize as the same UTF-8 bytes on both machines; never machine-locale-dependent escaping. The file/body is written/encoded as UTF-8 explicitly.
- **Stable numeric formatting** — all scores are integers (no floats, so no platform float-repr drift); move counts are integers.
- **No volatile fields in the emitted JSON** — no timestamps-of-send, no random nonces, no run UUIDs in the report body. `timezone` is a static config string, not a "now()" value. Anything non-deterministic would break the byte-identity guarantee.

```python
def canonical_json(payload: dict) -> str:
    """Serialize a report dict to a byte-stable canonical JSON string.

    Same logical input -> identical bytes, on any machine. This is the
    contract the inter-group bonus (E12) depends on: both groups feed the
    agreed result through this function and email the result; a single
    differing byte scores 0 for both.
    """
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
```

`builder.build_internal_game(state, config) -> dict` constructs the schema-shaped dict; `canonical_json(...)` turns it into the exact string that becomes both the on-disk `reports/internal_game.json` and the email body. The on-disk sample and the emailed body are produced by the *same* call, so what is committed to `reports/` is exactly what was sent.

---

## 4. pydantic schema validation before send

`report/schema.py` defines pydantic v2 models for both reports:

- `Student(id: str, name_en: str, name_he: str)`
- `SubGameResult(index: int, winner: Literal["cop","thief"], moves: int, capture: bool, cop_score: int, thief_score: int)`
- `Totals(cop: int, thief: int)`
- `InternalGameReport(group_name, students: list[Student], github_repo, cop_mcp_url, thief_mcp_url, timezone, sub_games: list[SubGameResult], totals: Totals)`
- `BonusGameReport(...)` — the §9.2 shape (4 MCP URLs, `totals_by_group`, `bonus_claim`, `mutual_agreement`) lives here too so both report types share one validation surface (used by Phase 11).

The pipeline is strict: **validate, then serialize, then send**. The Cop's end-of-game hook does:

```
report_dict = builder.build_internal_game(final_state, config)
InternalGameReport.model_validate(report_dict)   # raises on schema drift -> abort send
body = builder.canonical_json(report_dict)
gmail_sender.send(body, to=config.report.to)
```

If validation fails (wrong key set, fewer than 6 sub-games, a `winner` outside the enum, a totals mismatch), the send is **aborted** rather than emailing a malformed report. A malformed autonomous email would be worse than none: it could silently fail the bonus byte-match or be unreadable to the grader. Validation also catches an early-exit bug where the engine produced <6 valid sub-games (which ties directly into the Technical-Loss handling in §6).

---

## 5. Gmail-API sender

`report/gmail_sender.py` implements the OAuth → MIME → base64url → send chain. Heavy Google libraries are imported **lazily inside functions** (marked `# pragma: no cover`) so the test suite stays network-free and CI doesn't need the credentials (the lazy-import discipline from the tooling-port plan).

### 5.1 OAuth (Desktop client, `InstalledAppFlow`)

- The OAuth client is a **Desktop** application client created in a Google Cloud project with the **Gmail API enabled**. The downloaded client secrets file is renamed `credentials.json` and placed in the repo root — **gitignored** (rule 9; never committed).
- Scope: **`https://www.googleapis.com/auth/gmail.send`**. This is the *minimal sufficient* scope for "compose and send only" and is exactly what HW6 needs. Dr. Segal's guide uses `gmail.modify` (a broader scope that *also* permits send), so a token minted with `gmail.modify` works too — but `gmail.send` is the principled minimum and is preferred.
- First run: `InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES).run_local_server(port=0)` opens the browser consent screen, the user (added as a **Test user** in the project, since the app is in Testing mode) clicks through the "app isn't verified" warning, and the resulting credentials are persisted to **`token.json`** (also gitignored). Subsequent runs load `token.json` and **auto-refresh** the access token via the stored refresh token — no further consent. The `service` is built with `googleapiclient.discovery.build("gmail", "v1", credentials=creds)`.
- **Scope-change gotcha (documented for the human):** scopes are cached in `token.json`. Changing the requested scope requires **deleting `token.json`** to force a fresh consent; otherwise the cached, narrower/older scope is reused.

### 5.2 MIME body that *is* the raw JSON

The message body **is the canonical JSON string itself** — no prose, no greeting, no signature. We build a plain-text MIME message whose payload is the JSON, set `To` from `config.report.to`, set a minimal subject (the *subject* is metadata, not body; the spec's "JSON-only body" constraint is about the body), then **base64url-encode** the serialized MIME and send:

```python
def send(body: str, to: str) -> dict:
    """Send the raw report JSON as the email body via the Gmail API.

    `body` is the canonical-serialized JSON (the email body IS this JSON,
    no surrounding prose). Returns the Gmail API send response.
    """
    from email.mime.text import MIMEText        # pragma: no cover
    import base64                                 # pragma: no cover
    mime = MIMEText(body, _charset="utf-8")       # the JSON itself is the body
    mime["To"] = to
    mime["Subject"] = "COSMOS77-ex06 internal_game report"
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    service = _gmail_service()                     # OAuth/token.json, lazy import
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()
```

Key Gmail-API specifics, all asserted in tests against a mocked client:

- **`base64url`** (URL-safe base64), not standard base64 — the Gmail API rejects `+`/`/` in `raw`.
- **`userId="me"`** — sends as the authenticated account.
- **`service.users().messages().send(...)`** — the raw RFC-822 message is wrapped as `{"raw": <base64url>}`.
- UTF-8 charset on the MIME text so the canonical JSON's bytes (including Hebrew names) survive transport unaltered — preserving byte-identity for the bonus path.

### 5.3 Autonomous trigger (E7 / E5)

The **Cop agent** owns the trigger. When the orchestrator's runner reports that **6 valid sub-games** are complete, the Cop's end-of-game hook runs `build → validate → canonical_json → send` with **no manual step**. This is deliberate: the spec assigns the report to the cop, and routing it through the cop's end-of-game path keeps the autonomy guarantee inside the agent that "wins or loses" the pursuit. The CLI surface (`cosmos77-pursuit report --send`) exists only for the one-time human verification of OAuth consent; the *graded* path is the automatic one.

---

## 6. Technical-Loss handling (E13)

A **sub-game** can fail for non-game reasons: a cloud cold-start timeout, an MCP transport drop, a rate-limit on the LLM, a malformed/empty agent turn, or any protocol error that prevents a clean win/survive outcome. Such a sub-game is a **Technical-Loss**: it is **voided** (not scored, not counted toward the 6) and **re-run**. The pipeline must reach **6 valid sub-games** before the report is built; the runner loops, voiding-and-rerunning, until the valid count hits 6.

Implications for this module:

- The report's `sub_games[]` contains **exactly 6** entries, all valid; voided attempts never appear and never consume a 1-based `index`. `totals` accumulates only over valid sub-games.
- The builder asserts `len(sub_games) == config.num_games` (default 6) before constructing the dict; pydantic re-checks it. If the engine somehow yields <6 valid sub-games (e.g., it gave up after exhausting reruns), validation **fails and aborts the send** — better no email than a report claiming a complete game that wasn't.
- Because the *re-run* logic lives in `orchestrator/runner.py` (Phase 7) and the *void* decision is a game-engine concern, this module stays pure: it consumes a final, already-validated 6-sub-game state. The separation keeps `report/` deterministic and testable, and keeps the Technical-Loss policy in one place.

---

## 7. Testing strategy (rules 6, 7, 17)

All LLM/MCP/network/Gmail I/O is mocked; the report module targets the ≥85% coverage floor (rule 7 includes `report` explicitly).

- **Builder:** the builder emits **schema-valid** JSON for a fixture 6-sub-game state; `totals` equal the per-sub-game score sums; the key set exactly matches §9.1.
- **Canonical determinism:** the *same* logical input → **byte-identical** output across repeated calls and across reordered input dicts (the bonus contract). A golden-file comparison guards against accidental formatting changes.
- **JSON-only body:** the email body is parseable as JSON and contains **no** extra prose — `json.loads(body)` round-trips to the report dict.
- **Sender:** with a mocked `googleapiclient`, assert the payload is **base64url**-encoded, that `messages().send` is called with **`userId="me"`** and a `{"raw": ...}` body, and that the `To` is read from config.
- **Token refresh path:** an expired-credentials fixture exercises the auto-refresh branch (load `token.json` → refresh → reuse) without hitting Google.
- **Validation gate:** a deliberately-malformed report (5 sub-games, or a bad `winner`) raises in `model_validate` and the send is **not** attempted.
- **Determinism:** seed `random`, fix positions/scores, mock all I/O — no flakes (rule 17). Real-send tests, if any, carry the `live` marker and are excluded from CI (`-m 'not live'`).

---

## 8. Files and line budgets

| File | Responsibility | Cap |
|---|---|---|
| `report/output.py` | build internal-game dict from `GameState`/totals; `canonical_json` (shared with bonus) | ≤120 |
| `report/gmail_sender.py` | OAuth (Desktop, `gmail.send`), MIME=raw-JSON, base64url, `messages().send` | ≤120 |
| `report/schema.py` | pydantic models for internal-game **and** bonus JSON; validate-before-send | ≤100 |

All public classes/functions carry docstrings and type hints (rules 15, 16). Secrets (`credentials.json`, `token.json`) are gitignored (rule 9). Nothing is hardcoded that belongs in `config/config.yaml` (rule 4).

---

## 9. Acceptance mapping

| Criterion | How this module satisfies it |
|---|---|
| **E7** | Cop agent autonomously builds the §9.1 internal-game JSON and emails the **JSON-only body** to `rmisegal+uoh26b@gmail.com` via the Gmail API at the end of 6 valid sub-games. |
| **E13** | Report is built only over **6 valid** sub-games; Technical-Loss sub-games are voided and re-run upstream; builder + pydantic assert the count, aborting the send on any shortfall. |
| **E5 (support)** | The send is the terminal, fully autonomous step of the `init → 6 sub-games → report` pipeline — no manual intervention. |
| **E8 (support)** | Recipient, timezone, group metadata, and MCP URLs all read from `config/config.yaml`. |
| **E12 (support)** | The **canonical serializer** is shared with the bonus report so both groups can emit a **byte-identical** payload (mismatch → 0 for both). |
| **E3 (support)** | No LLM, no game-truth inside `report/`; it runs purely on the MCP-Client side, preserving Server/Client separation. |
