# PRD — Inter-Group Bonus Competition (E12)

> **Status:** Built **ready-to-activate**. The harness, schema, canonical serializer, and partner
> checklist are all delivered; the only thing missing at build time is a *partner group* and the
> four live cloud MCP URLs. The moment a partner group is secured, the series runs against the public
> cloud URLs and **both groups independently email a byte-identical `bonus_game` JSON**.
>
> **Course:** Orchestration of AI Agents (203.3763), Dr. Yoram Segal (UOH) — HW6.
> **Acceptance:** This document specifies **E12** (inter-group bonus, optional, ready-to-activate).
> It depends on **E2/E3** (two FastMCP servers, Server/Client separation), **E4** (free
> natural-language communication under partial observability), **E6** (public cloud HTTPS URLs +
> token auth), and **E7/E13** (canonical JSON report + Technical-Loss handling).
>
> **The prize:** **10 points on the final project** for both groups, plus a **HW5 deadline
> extension to 2026-07-03** for whoever submits the bonus. The deadline is within one week of the
> Friday lecture (the `bonus_game` email must be sent **before 08:30** on that Friday).

---

## 1. Why this exists — the bonus is *real money*, and the JSON must match exactly

The bonus is an **inter-group competition**: two groups play their already-built Cops & Robbers
pipelines against *each other* over the public internet, then each group emails a result report.
Everything that makes the single-group project hard — two autonomous agents coordinating in **free
natural language** over **MCP servers** under **partial observability**, with the **LLM living only
in the orchestrator (MCP Client)** and never inside `mcp_servers/` — still applies. The bonus simply
crosses the wires between two groups' deployments.

There is one make-or-break constraint that dominates the entire design of this harness:

> **Both groups must email *byte-identical* `bonus_game` JSON. If the two reports do not match,
> the grade is 0 for *both* groups.**

This is why the bonus is not "more game code". It is a **determinism and coordination problem**. The
core engineering risk is not who wins the pursuit — it is whether two *independently developed*
codebases can serialize the *same agreed result* to the *same bytes*. We solve this by:

1. Reusing the **exact same canonical serializer** that the single-group report uses (see
   `report/output.py`, PRD_report.md), so our side is deterministic by construction.
2. Publishing that serializer's rules as a **public contract** (§5) the partner group can replicate
   in any language.
3. Shipping a **`diff`-check** that both groups run *before sending* so a mismatch is caught while
   it is still fixable (§8).

The grade for HW6 as a whole is **the orchestration, not the game strategy**. The bonus rewards the
same thing one level up: it proves our autonomous, natural-language, cloud-MCP pipeline is robust
enough to interoperate with a *foreign* pipeline it has never seen.

---

## 2. Series structure — the role-swap (6 sub-games, symmetric)

The bonus is a single **inter-group game of 6 sub-games**, played as a **role-swap series** so each
group plays *both* roles against the other. Below, **OUR group = COSMOS77** (`group_1`) and **THEIR
group = the partner** (`group_2`). The orientation of `group_1`/`group_2` is fixed at coordination
time and used identically by both groups (§5).

| Sub-games | Cop side (server) | Thief side (server) | Our role |
|---|---|---|---|
| **1 – 3** | **OUR** cop MCP server | **THEIR** thief MCP server | We pursue |
| **4 – 6** | **THEIR** cop MCP server | **OUR** thief MCP server | We evade |

Properties of the swap:

- **Symmetry.** Each group spends 3 sub-games as the cop and 3 as the thief, so neither side is
  advantaged by the asymmetric scoring table (cop capture is worth more than thief survival).
- **Cross-group wiring.** In every sub-game the **orchestrator (MCP Client) connects to one cop
  server and one thief server that belong to *different groups*.** The orchestrator still owns the
  LLM and the turn loop; the two foreign FastMCP servers expose **tools only** (`get_local_observation`,
  `apply_move`, `place_barrier`, `send_message`, `receive_messages`, `verify_position`). The
  Server/Client separation (E3) is preserved across the group boundary.
- **Partial observability is unchanged.** Each agent still receives only its **local/partial view**
  from its own server and must **infer the opponent's position from the opponent's free-language
  messages**. The fact that the opponent is now a *foreign* LLM makes the natural-language inference
  harder and more interesting — exactly the orchestration challenge the course rewards.
- **Free natural language across groups.** The two agents exchange **free natural-language messages**
  (intentions, partial observations, possibly bluffs). There is **no rigid numeric protocol**. The
  only thing the two groups agree on in advance is the *transport* (MCP tool names + token auth) and
  the *result schema* — never the *content* of the conversation.

### 2.1 Who runs the engine

Per the spec, the two groups must **agree who runs the orchestration engine** for each sub-game. Two
patterns are supported by `bonus/series.py`:

- **Single-engine (recommended for simplicity).** One agreed group runs the orchestrator for all 6
  sub-games against the four cloud URLs; both groups observe the transcript and totals. The running
  group shares the per-sub-game results; both groups then *independently* serialize the agreed
  `bonus_game` JSON and email it.
- **Dual-engine (mirror).** Both groups run the engine independently against the same four cloud URLs
  with the **same agreed configuration** (grid, seeds if any, move limit). The two runs must produce
  the same `totals_by_group` and `bonus_claim`; the per-move transcript may differ slightly (the
  LLMs are stochastic), so **only the *agreed result fields* are serialized into the report** — never
  the raw transcript — which keeps the two reports byte-identical regardless of who ran the engine.

Either way, the serialized `bonus_game` JSON contains only the **agreed, deterministic result
fields**, not the stochastic conversation. This decoupling is what makes byte-identical reports
achievable between two different codebases.

---

## 3. Scoring — per sub-game, totals by group, and the `bonus_claim`

### 3.1 Per-sub-game scoring (same table as the single-group game)

Each sub-game is scored with the project's standard scoring table (config-driven,
`config/config.yaml → scoring`), credited to whichever **group** owned the winning side:

| Outcome | Cop side gets | Thief side gets |
|---|---|---|
| **Capture** (cop lands on thief's cell within `max_moves`) | `cop_win = 20` | `thief_loss = 5` |
| **Survival** (thief survives all `max_moves = 25` moves) | `cop_loss = 5` | `thief_win = 10` |

Because of the role-swap, the points flow to the *group* that owned the cop/thief server in that
sub-game. Example: in sub-game 2, OUR cop captures THEIR thief → `group_1 (COSMOS77)` += 20 (cop_win),
`group_2 (partner)` += 5 (thief_loss).

### 3.2 Totals by group

`totals_by_group` sums each group's points across **all 6 sub-games** (its 3 cop sub-games + its 3
thief sub-games). This is the field that decides the series.

### 3.3 The `bonus_claim` — averaged across the series, per spec

The **per-group bonus award** is computed from the series outcome (who has the higher
`totals_by_group`). Per the playbook/spec, the award schedule is:

| Series result for a group | `bonus_claim` points |
|---|---|
| **Win** (higher total) | **10** |
| **Tie** (equal totals) | **5** |
| **Lose** (lower total) | **7** |

> **Note on "averaged across the series".** The *series* result is what is averaged/aggregated:
> `bonus_claim` is a function of the **summed `totals_by_group` over all 6 sub-games**, not of any
> single sub-game. A group's claim is therefore the single value (10 / 7 / 5) implied by the
> aggregate series outcome. Both groups compute their own claim from the *same* `totals_by_group`,
> and both claims appear in the report (one per group) — they must agree on each other's claim too,
> which is part of `mutual_agreement: true`.

`bonus/report.py` computes `bonus_claim` deterministically from `totals_by_group`; the tie/win/lose
thresholds come from a `bonus.claim` block in `config/config.yaml` (never hardcoded — Rule 4 / E8).

---

## 4. The `bonus_game` JSON schema (spec §9.2)

The report sent by *each* group is a single JSON object with `report_type: "bonus_game"`. It carries
the two groups' identities, all **four** cloud MCP URLs, the per-sub-game results, the totals, the
bonus claim, and the explicit `mutual_agreement: true` flag. Below is the canonical shape; the
pydantic model lives in `report/schema.py` (shared with the single-group schema) and validation runs
before any email is sent.

```json
{
  "report_type": "bonus_game",
  "groups": {
    "group_1": "COSMOS77",
    "group_2": "PARTNER_GROUP_CODE"
  },
  "github_repo_group_1": "https://github.com/AbdallahKhaldi/COSMOS77-ex06",
  "github_repo_group_2": "https://github.com/<partner>/<partner-repo>",
  "mcp_url_group_1_cop":   "https://<our-cop>.example/mcp",
  "mcp_url_group_1_thief": "https://<our-thief>.example/mcp",
  "mcp_url_group_2_cop":   "https://<their-cop>.example/mcp",
  "mcp_url_group_2_thief": "https://<their-thief>.example/mcp",
  "timezone": "Asia/Jerusalem",
  "students_group_1": [
    {"id": "212389712", "name": "Abdallah Khaldi"},
    {"id": "323118794", "name": "Tasneem Natour"}
  ],
  "students_group_2": [
    {"id": "<id>", "name": "<name>"}
  ],
  "sub_games": [
    {
      "index": 1,
      "cop_group": "group_1",
      "thief_group": "group_2",
      "result": "capture",
      "moves": 14,
      "cop_score": 20,
      "thief_score": 5
    },
    {
      "index": 2,
      "cop_group": "group_1",
      "thief_group": "group_2",
      "result": "survival",
      "moves": 25,
      "cop_score": 5,
      "thief_score": 10
    }
    // ... sub-games 3..6; index 4-6 swap cop_group->group_2, thief_group->group_1
  ],
  "totals_by_group": {
    "group_1": 75,
    "group_2": 60
  },
  "bonus_claim": {
    "group_1": 10,
    "group_2": 7
  },
  "mutual_agreement": true
}
```

### 4.1 Field reference

| Field | Type | Meaning |
|---|---|---|
| `report_type` | `"bonus_game"` | Distinguishes the bonus report from the single-group `internal_game` report (E7). |
| `groups.group_1` / `group_2` | string | The two group codes; orientation fixed at coordination time. |
| `github_repo_group_1` / `_2` | string (URL) | Each group's public repo. |
| `mcp_url_group_1_cop` / `_1_thief` / `_2_cop` / `_2_thief` | string (HTTPS URL) | The **four** public cloud MCP endpoints used in the series (E6). |
| `timezone` | string | IANA TZ for timestamping; `Asia/Jerusalem` from config. |
| `students_group_1` / `_2` | list of `{id, name}` | The members of each group. |
| `sub_games` | list (length 6) | Per-sub-game result: `index`, which group was cop/thief, `result` (`capture`/`survival`), `moves`, and the two scores. |
| `totals_by_group` | `{group_1, group_2}` | Summed points across all 6 sub-games (§3.2). |
| `bonus_claim` | `{group_1, group_2}` | Each group's award (10/7/5) from the series outcome (§3.3). |
| `mutual_agreement` | `true` | Both groups have inspected and agreed to this exact report. **Must be `true`** for the bonus to count. |

> **`mutual_agreement` is not cosmetic.** Setting it to `true` is the explicit attestation that both
> groups looked at the *same* result and the *same* bytes. It is the human checkpoint that pairs with
> the machine `diff` (§8): the diff proves the bytes match; `mutual_agreement: true` proves both
> groups *intended* them to.

---

## 5. The canonical serializer — the same one the single-group report uses

Byte-identical output between two independent codebases is only possible if both sides serialize
under the **same canonical rules**. We **reuse the exact serializer from `report/output.py`**
(PRD_report.md, E7); the bonus does not invent a second one. `bonus/report.py` calls the shared
`canonical_json(...)` helper.

### 5.1 The canonical contract (publish this verbatim to the partner)

The serializer guarantees a single, reproducible byte string for a given result object:

1. **JSON, UTF-8, no BOM.**
2. **Keys sorted** lexicographically at every level (`sort_keys=True`). Object key order is therefore
   *not* a degree of freedom — the order shown in §4 is illustrative; the bytes are sorted.
3. **Pretty-printed with `indent=2`** — the canonical form uses `json.dumps(..., indent=2)` (two-space
   indentation, the default `", "` / `": "` item/key separators that `indent` implies). This is the
   *only* formatting both groups use; do **not** substitute compact `separators=(",", ":")`.
4. **`ensure_ascii=False`** — non-ASCII (e.g., the Hebrew name forms, if included) are emitted as raw
   UTF-8, not `\uXXXX` escapes. Both groups must use the *same* setting; the contract is
   `ensure_ascii=False`.
5. **One trailing newline** appended to the serialized text (`text + "\n"`) — the file ends in exactly
   one `\n`. Both groups must write the file with this single trailing newline, since the file content
   is the byte body both sides diff and email.
6. **Numbers are integers** for all scores/totals/claims/indices/moves — no floats, no `20.0`.
7. **Booleans lowercase** (`true`/`false`) per JSON.
8. **Fixed value normalization:** group codes, repo URLs, MCP URLs, IDs, and names are agreed as
   *exact strings* during coordination (§7) — including casing, trailing slashes on URLs, and the
   order of the `students_*` lists and the `sub_games` list. Lists are **ordered**, so both groups
   must agree on the ordering before serializing.

In code (shared helper, illustrative):

```python
import json

def canonical_json(obj: dict) -> str:
    """Single canonical byte-string for a report dict (shared by E7 and E12)."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
    )

# The file written / emailed is `canonical_json(obj) + "\n"` (one trailing newline).
```

### 5.2 Why reuse, not re-implement

- **Determinism by construction on our side.** The same function already passes the E7 report tests
  for byte-stability (same input → identical bytes); the bonus inherits that guarantee for free.
- **One contract to communicate.** We hand the partner the eight rules above (and ideally the helper
  itself). Any language that can produce sorted-key, `indent=2`, UTF-8 JSON of the agreed value object
  (plus the single trailing newline) will match us — the partner does not need our Python.
- **The agreed *value object* is the real interface.** Two codebases match iff (a) they hold the
  *same dict* (same group orientation, same per-sub-game results, same totals, same claim, same
  ordering of lists) and (b) they apply the *same* canonical rules. §7 nails down (a); §5.1 nails
  down (b); §8 verifies both.

---

## 6. Module design (ready-to-activate code)

All modules obey the 17 rules: ≤150 lines per file, config-driven (no hardcoded grid/scoring/URLs/
tokens), docstrings + type hints on public signatures, deterministic tests with all LLM/MCP/network
I/O mocked.

### 6.1 `src/cosmos77_ex06/bonus/series.py` (≤150 lines)

Orchestrates the **role-swap series** over the four public cloud URLs.

- Reads a **`bonus` config block** (the four MCP URLs, the shared bonus token, the group orientation,
  who runs the engine) from `config/config.yaml` — nothing hardcoded.
- For sub-games 1–3: wires the orchestrator's two FastMCP `Client`s to **OUR cop URL** and **THEIR
  thief URL**. For sub-games 4–6: **THEIR cop URL** and **OUR thief URL**.
- Delegates each sub-game to the existing `GameEngine` (orchestrator) — the same LLM-in-the-client,
  free-natural-language loop used in the single-group game. The bonus adds **no** new game logic and
  **no** LLM inside any server.
- Applies **Technical-Loss handling (E13)**: a sub-game that fails technically (network drop, cloud
  cold-start, auth error against a foreign server) is **voided and re-run** until 6 valid sub-games
  exist. This matters more in the bonus because half the servers are foreign.
- Returns the ordered list of 6 sub-game results + the role map, ready for `bonus/report.py`.

### 6.2 `src/cosmos77_ex06/bonus/report.py` (≤120 lines)

Builds and serializes the `bonus_game` JSON.

- Assembles the agreed **value object** (§4) from the series results + the coordination metadata
  (group codes, repos, students, the four URLs, timezone).
- Computes `totals_by_group` (§3.2) and `bonus_claim` (§3.3) deterministically from config thresholds.
- Validates against the `report/schema.py` pydantic model.
- Serializes via the **shared `canonical_json`** (§5) — the *same* function as the single-group
  report — guaranteeing byte-stability.
- Hands the canonical string to the **same Gmail sender** (`report/gmail_sender.py`) used for E7: a
  JSON-only MIME body, base64url-encoded, `to = config.report.to` for the course target, and to the
  agreed bonus recipient(s) as coordinated. (Both groups send their own email.)

### 6.3 `src/cosmos77_ex06/bonus/coordinate.md` (the partner checklist — §7) + `bonus/diff_check.py` (§8)

A human-facing checklist plus a tiny script that compares two `bonus_game` JSON files byte-for-byte
before either group sends.

### 6.4 Config block (added to `config/config.yaml`, ready-to-activate)

```yaml
bonus:
  enabled: false                 # flip to true once a partner is secured
  group_1: "COSMOS77"            # orientation, fixed at coordination time
  group_2: "PARTNER_GROUP_CODE"
  github_repo_group_2: "https://github.com/<partner>/<partner-repo>"
  students_group_2:
    - {id: "<id>", name: "<name>"}
  mcp:
    group_1_cop:   "https://<our-cop>.example/mcp"
    group_1_thief: "https://<our-thief>.example/mcp"
    group_2_cop:   "https://<their-cop>.example/mcp"
    group_2_thief: "https://<their-thief>.example/mcp"
  engine_runner: "group_1"       # who runs the orchestrator (single-engine pattern)
  claim: {win: 10, lose: 7, tie: 5}
```

The shared **bonus token** lives in `.env` (`BONUS_MCP_TOKEN`), never in the repo (Rule 9). Token
auth is revocable: rotating the token immediately cuts off cross-group access after the series.

---

## 7. Partner coordination checklist

Run through this with the partner group **before** the engine runs. Everything here feeds the
*agreed value object* that must serialize identically on both sides.

**A. Pairing & orientation**
- [ ] Secure a partner group; exchange group codes. **Agree the orientation:** who is `group_1`,
      who is `group_2`. Both sides record the *identical* orientation. (Reversing it produces a
      different — but still mismatched — report, so this must be pinned first.)
- [ ] Exchange **public GitHub repo URLs** (exact strings, including casing).
- [ ] Exchange **student rosters** as `{id, name}` lists, and **agree the list order** for each
      group's `students_*` array.

**B. Deployment & transport (E2/E3/E6)**
- [ ] Each group deploys its **two FastMCP servers** to **public HTTPS URLs** (Prefect Horizon /
      FastMCP Cloud, or a `cloudflared`/ngrok/Localtonet tunnel — the spec is platform-agnostic).
- [ ] Exchange the **four MCP URLs** (`group_1_cop`, `group_1_thief`, `group_2_cop`, `group_2_thief`)
      as exact strings (mind trailing slashes and the `/mcp` path).
- [ ] Agree a **shared bonus token** for cross-group auth; each group sets it in its server env and
      the orchestrator attaches it. Confirm both sides can reach all four URLs and list tools.
- [ ] Confirm each foreign server exposes the **same tool names** the orchestrator expects
      (`get_local_observation`, `apply_move`, `place_barrier`, `send_message`, `receive_messages`,
      `verify_position`). The conversation content is free language; only the *tool surface* is agreed.

**C. Game configuration (must be identical on both sides)**
- [ ] Agree the **grid size**, `max_moves` (25), `max_barriers` (5, cop only), `allow_diagonal`
      (true), `turn_order` (thief → cop), and the **scoring table** (cop_win 20 / thief_loss 5 /
      thief_win 10 / cop_loss 5).
- [ ] Agree the **role-swap** mapping (sub-games 1–3 group_1 cop; 4–6 group_2 cop).
- [ ] Agree **who runs the engine** (single-engine, recommended) or that both mirror it (dual-engine).
- [ ] If any seeding is used, agree the seeds (the *transcript* is stochastic regardless; only the
      *result fields* are serialized).

**D. Run & agree the result**
- [ ] Run the **6 sub-games** over the cloud URLs; apply **Technical-Loss** voids+reruns until 6 are
      valid (E13).
- [ ] Both groups inspect the **per-sub-game results**, `totals_by_group`, and `bonus_claim` and
      confirm they agree on every value.
- [ ] Each group independently builds its `bonus_game` JSON via its own `bonus/report.py`.

**E. Diff, agree, send**
- [ ] Run the **`diff`-check** (§8) on the two JSON files. It must report **identical bytes**.
- [ ] Set `mutual_agreement: true` only after the diff is clean and both groups have eyeballed the
      report.
- [ ] Each group **independently emails** its (now byte-identical) `bonus_game` JSON to the course
      target (`rmisegal+uoh26b@gmail.com`) and any agreed recipient — **before 08:30** on the bonus
      Friday.

---

## 8. The `diff`-check before sending (mismatch → 0 for both)

A mismatch means **0 points for both groups**, so the diff is mandatory and runs **before** either
group hits send. `bonus/diff_check.py` compares the two canonical JSON strings byte-for-byte and
exits non-zero on any difference, with a human-readable report of *where* they diverge.

```bash
# Each group produces its canonical bonus_game JSON. Our side runs the engine, which
# writes reports/bonus_game.json (canonical: sort_keys, ensure_ascii=False, indent=2,
# one trailing newline):
uv run cosmos77-pursuit bonus --partner config/                          # our side
# (partner produces reports/bonus_group_2.json with their codebase)

# Compare byte-for-byte before anyone emails — the simple, total check:
diff -q reports/bonus_game.json reports/bonus_group_2.json \
  && echo "IDENTICAL -> safe to set mutual_agreement:true and send" \
  || echo "MISMATCH -> DO NOT SEND; reconcile the value object first"

# Or, with localization of the offending field (Python helper, same verdict):
uv run python -c "from cosmos77_ex06.bonus.diff_check import diff_files, format_result; \
print(format_result(diff_files('reports/bonus_game.json', 'reports/bonus_group_2.json')))"
```

The check is intentionally dumb and total — a raw byte comparison of the two files, plus (on
mismatch) a normalized key-by-key diff to localize the offending field. Common mismatch causes it
surfaces, mapped to the §5.1 contract:

| Symptom | Root cause | Fix |
|---|---|---|
| Same data, different byte order | one side didn't `sort_keys` | apply the canonical serializer |
| Different indentation / spacing | different `indent` | both use `indent=2` |
| `ע...` vs raw Hebrew | different `ensure_ascii` | both use `ensure_ascii=False` |
| `20.0` vs `20` | a score became a float | force ints |
| One byte longer/shorter | trailing newline mismatch | contract = exactly one trailing `\n` |
| `group_1` totals swapped | orientation disagreement | re-confirm §7-A orientation |
| `sub_games`/`students_*` reordered | list order not agreed | re-confirm §7-A/C ordering |

A clean diff is the precondition for `mutual_agreement: true`. The two together — machine-verified
identical bytes **and** explicit mutual agreement — are what protect the 10 points.

---

## 9. Testing (all mocked, deterministic — Rule 6/17)

`tests/unit/test_bonus/` covers the harness with **no live LLM, MCP, network, or Gmail**:

- **Role assignment.** `series.py` assigns sub-games 1–3 to `group_1` cop / `group_2` thief and 4–6
  to the swap; asserts the four URLs are wired to the correct sides per sub-game.
- **Schema validity.** `bonus/report.py` emits a `bonus_game` object that validates against the
  `report/schema.py` pydantic model, including all four URLs and `mutual_agreement: true`.
- **Canonical determinism.** The shared serializer is **deterministic**: the same value object →
  **identical bytes** across repeated calls and across dict insertion orders (sorted keys prove it).
- **Cross-codebase parity (simulated).** A second dict built in a *different key order* serializes to
  the *same* bytes as the canonical one — the property a partner codebase relies on.
- **Scoring & claim.** `totals_by_group` sums correctly across the 6 role-swapped sub-games;
  `bonus_claim` resolves to 10 (win) / 7 (lose) / 5 (tie) from config thresholds on hand-computed
  fixtures.
- **Diff-check.** Identical files → exit 0 / "IDENTICAL"; a one-byte change → exit non-zero with the
  offending location reported.
- **Technical-Loss in the series.** A simulated foreign-server failure in a sub-game is voided and
  re-run so the series still yields exactly 6 valid sub-games (E13).

---

## 10. Acceptance mapping

| Item | Where satisfied |
|---|---|
| **E12** inter-group bonus, role-swap series, matching `bonus_game` JSON, `mutual_agreement` | this PRD; `bonus/series.py`, `bonus/report.py`, `bonus/coordinate.md`, `bonus/diff_check.py` |
| **E2/E3** two FastMCP servers, LLM in client only (across the group boundary) | series wires foreign servers as tool-only endpoints; orchestrator owns the LLM |
| **E4** free natural language under partial observability (now vs a foreign agent) | reuses the orchestrator NL loop; only transport + result schema are agreed, never message content |
| **E6** public cloud HTTPS URLs + revocable token auth | four cloud URLs + shared `BONUS_MCP_TOKEN`; rotation revokes access |
| **E7** canonical JSON report + Gmail sender | shared `canonical_json` + `report/gmail_sender.py`; JSON-only body |
| **E13** Technical-Loss handling | series voids + reruns failed sub-games to reach 6 valid |
| **Rules 1/4/6/9/15/16/17** | ≤150-line files, config-driven (`bonus` block), mocked deterministic tests, token in `.env`, docstrings + type hints |

---

## 11. Definition of done (ready-to-activate)

- [x] Series, report, diff-check modules implemented (≤150 lines each), all I/O mocked in tests.
- [x] `bonus` config block present with `enabled: false` and placeholders for the partner's identity
      and the four URLs.
- [x] Shared canonical serializer reused from the single-group report (byte-stability proven by tests).
- [x] Partner coordination checklist (§7) and `diff`-check (§8) documented and scripted.
- [ ] **Activation (human touchpoint):** secure a partner group, fill the `bonus` block + `.env`
      token, deploy/confirm the four cloud URLs, run the 6 sub-games, run the diff, set
      `mutual_agreement: true`, and **both groups email the byte-identical `bonus_game` JSON before
      08:30** on the bonus Friday.
