# Inter-group BONUS — partner coordination checklist (E12, spec §12)

> **The bonus is real money:** 10 project points for both groups + a HW5 deadline
> extension to **2026-07-03** for whoever submits it. **Make-or-break rule:** both
> groups must email **byte-identical** `bonus_game` JSON. If the two reports differ,
> the grade is **0 for both**. Run the `diff`-check (§E) before anyone hits send.

Work top-to-bottom with the partner group **before** the engine runs. Everything
here feeds the *agreed value object* that must serialize identically on both sides.

## A. Pairing & orientation
- [ ] Secure a partner group; exchange group codes. **Agree the orientation:** who
      is `group_1` (= COSMOS77, by default OUR group) and who is `group_2`. Both
      sides record the *identical* orientation (reversing it produces a mismatch).
- [ ] Exchange **public GitHub repo URLs** as exact strings (mind casing / trailing slash).
- [ ] Exchange **student rosters** as `{id, name}` lists and **agree the list order**
      for each group's `students_group_*` array (lists are ordered, so order matters).

## B. Deployment & transport (E2/E3/E6)
- [ ] Each group deploys its **two FastMCP servers** to **public HTTPS URLs**
      (Prefect Horizon / FastMCP Cloud, or a `cloudflared`/ngrok tunnel).
- [ ] Exchange the **four MCP URLs** (`group_1_cop`, `group_1_thief`, `group_2_cop`,
      `group_2_thief`) as exact strings (mind the `/mcp` path + trailing slashes).
- [ ] Agree a **shared bonus token**; set it in `.env` as `BONUS_MCP_TOKEN` on both
      sides (never in the repo — Rule 9). Confirm all four URLs list tools with it.
- [ ] Confirm each foreign server exposes the expected tool surface
      (`get_local_observation`, `apply_move`, `place_barrier`, `send_message`,
      `receive_messages`, `verify_position`). Only the *transport* is agreed — never
      the *content* of the free natural-language conversation (E4).

## C. Game configuration (must be identical on both sides)
- [ ] Agree `grid_size`, `max_moves` (25), `max_barriers` (5, cop only),
      `allow_diagonal` (true), `turn_order` (thief → cop), and the scoring table
      (cop_win 20 / thief_loss 5 / thief_win 10 / cop_loss 5).
- [ ] Agree the **role-swap**: sub-games **1-3** group_1 cop vs group_2 thief;
      sub-games **4-6** group_2 cop vs group_1 thief.
- [ ] Agree the `bonus.claim` schedule: win 10 / lose 7 / tie 5.
- [ ] Agree **who runs the engine** (single-engine, recommended) — `engine_runner`
      in the `bonus` config block.

## D. Fill the config & run
- [ ] Fill the `bonus` block in `config/config.yaml` (group_2 code + repo + students,
      the four `bonus.mcp.*` URLs) and set `bonus.enabled: true`; set `BONUS_MCP_TOKEN`.
- [ ] Run the **6 sub-games** over the cloud URLs; Technical-Losses are voided + re-run
      until 6 valid sub-games exist (E13):
      ```bash
      uv run cosmos77-pursuit bonus --partner config/   # writes reports/bonus_game.json
      ```
- [ ] Both groups inspect the per-sub-game results, `totals_by_group`, and
      `bonus_claim` and confirm they agree on every value.

## E. Diff, agree, send (mismatch → 0 for both)
Each group produces its canonical `bonus_game` JSON, then compare **byte-for-byte**
before anyone emails:

```bash
# Our side writes reports/bonus_game.json (canonical: sort_keys, ensure_ascii=False, indent=2).
# The partner produces reports/bonus_group_2.json with their own codebase.

# Byte-for-byte compare — the simple, total check:
diff -q reports/bonus_game.json reports/bonus_group_2.json \
  && echo "IDENTICAL -> safe to set mutual_agreement:true and send" \
  || echo "MISMATCH -> DO NOT SEND; reconcile the value object first"

# Or, with localization of the offending field (Python helper, same verdict):
uv run python -c "from cosmos77_ex06.bonus.diff_check import diff_files, format_result; \
print(format_result(diff_files('reports/bonus_game.json', 'reports/bonus_group_2.json')))"
```

Common mismatch causes (mapped to the canonical contract, §5.1 of PRD_bonus.md):

| Symptom | Root cause | Fix |
|---|---|---|
| Same data, different byte order | one side didn't `sort_keys` | use the shared canonical serializer |
| `ע…` vs `\uXXXX` | different `ensure_ascii` | both use `ensure_ascii=False` |
| `20.0` vs `20` | a score became a float | force ints |
| One byte longer | trailing newline on one side | agree on the trailing newline |
| `group_1` totals swapped | orientation disagreement | re-confirm §A orientation |
| `sub_games`/`students_*` reordered | list order not agreed | re-confirm §A/§C ordering |

- [ ] The `diff` reports **IDENTICAL**. Only then set `mutual_agreement: true`.
- [ ] Each group **independently emails** the (now byte-identical) `bonus_game` JSON
      to `rmisegal+uoh26b@gmail.com` (JSON-only body) and any agreed recipient —
      **before 08:30** on the bonus Friday.
