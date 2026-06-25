# PRD — The Formal Model: Cops & Robbers as a Dec-POMDP

> **Scope.** This document gives the formal, mathematical model of the COSMOS77-ex06 pursuit
> game as a **Decentralized Partially Observable Markov Decision Process (Dec-POMDP)**. It
> defines every element of the canonical tuple **⟨n, S, {A_i}, P, R, {Ω_i}, O, γ⟩** concretely
> for *this* game (config-driven 5×5 grid, two agents, free natural-language communication,
> partial observability), characterizes the **state space** and **observation space** sizes,
> and argues why the combination of partial observability + free-language coordination makes
> this a genuine **decentralized** control problem rather than a centrally-solved game.
>
> **Audience / downstream.** This is the formal substrate for the scientific README (Phase 10,
> acceptance criterion **E11**). It is also the conceptual contract the implementation must
> honor: §"What the model forces the code to do" below maps each tuple element to the modules
> that realize it (`game/`, `mcp_servers/`, `orchestrator/`, `agents/`).
>
> **The grading reminder.** Per the spec and `CLAUDE.md`, the grade is the **orchestration** —
> two autonomous agents coordinating in free natural language over MCP under partial
> observability — **not** the pursuit strategy. The Dec-POMDP framing exists to make that
> orchestration challenge precise and measurable, not to optimize the chase.

---

## 1. Why a Dec-POMDP (and not an MDP, POMDP, or POSG)

The pursuit looks, superficially, like a toy grid game. The formalism matters because it names
exactly *which* difficulty the assignment rewards.

| Model | What it assumes | Why it is **wrong** for this game |
|---|---|---|
| **MDP** (Markov Decision Process) | One agent, full observability of the state. | We have **two** agents and **neither** sees the full state — the cop never knows the thief's exact cell, and vice versa. |
| **POMDP** (Partially Observable MDP) | One agent (or one central controller) with a noisy/partial observation, optimizing a single policy. | There is **no central controller acting on behalf of both players**. Each agent decides for itself from its own local view. |
| **POSG** (Partially Observable Stochastic Game) | Multiple agents, partial observability, **distinct** reward functions (general-sum / competitive). | Closest neighbour, and indeed Cop-vs-Thief is competitive. We adopt the **Dec-POMDP** lens because the assignment's *graded* object is the **coordination/communication protocol under shared partial observability**, and Dec-POMDP is the canonical model for *decentralized decision-making with local observations and inter-agent communication*. We treat the competitive reward split (§5) as the role-asymmetric instantiation of R. |

The decisive features that force the **Dec / PO** qualifiers:

1. **Decentralized (Dec).** Each agent runs its **own** decision loop. In our architecture
   (E3 — Server/Client separation) the *only* place a policy is computed is the orchestrator's
   per-role LLM call; the cop's reasoning and the thief's reasoning are **separate prompt
   contexts** that never share hidden state. There is no joint policy with global state access.
2. **Partially Observable (PO).** A role's tool `get_local_observation(role)` returns **only**
   that role's legitimate view — own position, the contents of cells within a vision radius,
   the barrier cells it knows about, the move counter, and the **opponent's last
   natural-language message**. It **never** returns the opponent's exact coordinates (E4). The
   true world state is therefore *hidden*; each agent must maintain a **belief** over where the
   opponent is.
3. **Communication as a first-class action.** The agents are allowed — required — to exchange
   **free natural-language messages** each turn. In Dec-POMDP terms, messaging is an *action*
   that shapes the *other* agent's *observation* on the next step. This is the crux of the
   assignment: the protocol is **not** a fixed numeric channel; it is open-ended language that
   may inform, mislead (bluff), or probe.

So the right one-line summary is: **a two-agent, role-asymmetric, communicative Dec-POMDP with
deterministic transitions and partial observability, where the communication channel carries
free natural language.**

---

## 2. The tuple at a glance

We model the game as

**M = ⟨ n, S, {A_i}, P, R, {Ω_i}, O, γ ⟩**

| Symbol | Name | This game |
|---|---|---|
| **n** | number of agents | **2** — agent 1 = **Cop** (pursuer), agent 2 = **Thief** (evader). |
| **S** | global state space | joint positions of cop & thief + the set of placed barrier cells + the move counter + the message ledger. |
| **{A_i}** | per-agent action sets | the (up to) **8 directional moves** + *stay*; the **Cop additionally** has *place-barrier*; **both** emit a free natural-language **message** each turn. |
| **P** | transition function | **deterministic**: legal moves apply; illegal/blocked/out-of-bounds moves are **no-ops**; barriers persist; the counter increments. |
| **R** | reward function | the **spec scoring table** as terminal rewards: cop_win 20 / thief_loss 5 ; thief_win 10 / cop_loss 5. |
| **{Ω_i}** | per-agent observation spaces | own position + the vision-radius cells + known barriers + move counter + the **opponent's last NL message**. |
| **O** | observation function | maps the true global state (+ messages) to each role's *partial* local observation; never leaks the opponent's exact cell. |
| **γ** | discount factor | **γ = 1** within a ≤25-move sub-game (finite, undiscounted horizon); see §8. |

Each element is defined precisely below.

---

## 3. n — the agents

**n = 2.**

- **Agent 1 — Cop (pursuer).** Goal: **capture** the thief by landing on the thief's cell
  within the move limit. Capability asymmetry: the cop may **place barriers** (≤ `max_barriers`
  = 5 per sub-game), turning chosen cells impassable to *both* agents — a tool for cutting off
  escape routes.
- **Agent 2 — Thief (evader).** Goal: **survive** until the move limit is reached
  (`max_moves` = 25). No barrier-placement capability.

The roles are **fixed within a sub-game** but **swap across the bonus series** (E12): in the
inter-group bonus, group A plays cop while group B plays thief for three sub-games, then the
roles invert. The Dec-POMDP structure is identical under swap; only the reward attribution and
the capability set move with the role.

> **Architectural note (E3).** "Agent" here is a *logical decision-maker*, realized as a
> per-role LLM context inside the **orchestrator / MCP-Client**. The two FastMCP servers
> (`cop_server`, `thief_server`) are **not** agents — they hold no policy and no LLM; they only
> expose tools. The Dec-POMDP's decentralization lives in the orchestrator's two separate
> reasoning contexts, *not* in the servers.

---

## 4. S — the global (hidden) state space

A global state **s ∈ S** is the full ground truth of one sub-game at one tick. The model does
**not** assume any single agent can observe `s`; `s` exists only as the authoritative object the
game state-machine (`game/state.py`) maintains and the MCP tools read through `O`.

A state is the tuple:

```
s = ( pos_cop , pos_thief , B , t , msg_ledger )
```

| Component | Domain | Meaning |
|---|---|---|
| `pos_cop` | a grid cell `(x, y)` with `0 ≤ x < W`, `0 ≤ y < H` | the cop's current cell. |
| `pos_thief` | a grid cell `(x, y)` | the thief's current cell. |
| `B` | a subset of grid cells, `\|B\| ≤ max_barriers` | the **barrier set** — cells made impassable to both agents by the cop. |
| `t` | integer, `0 ≤ t ≤ max_moves` | the **move counter** (turns elapsed in the sub-game). |
| `msg_ledger` | a sequence of `(role, text)` pairs | the running transcript of natural-language messages (the *communication state*). |

The grid dimensions `W × H`, `max_moves`, and `max_barriers` all come from `config/config.yaml`
(rule 4 / E8): default **W = H = 5**, `max_moves = 25`, `max_barriers = 5`. The **sanity ladder**
(2×2 → 3×3 → 4×4 → 5×5) is exactly a sequence of state spaces of growing cardinality, used to
validate the pipeline before scaling up.

### 4.1 Size of the state space

Let `N = W·H` be the number of cells (N = 25 on the default board). The *positional* part of the
state — the part that actually drives the pursuit — has cardinality bounded by:

- choices for `pos_cop`: at most **N** (must not be a barrier cell);
- choices for `pos_thief`: at most **N** (distinct from the cop pre-capture, not a barrier);
- choices for the barrier set `B`: any subset of the remaining cells of size 0..`max_barriers`,
  i.e. `Σ_{k=0}^{max_barriers} C(N, k)`;
- the counter `t`: `max_moves + 1` values.

So the **positional-plus-barrier-plus-counter** state count is on the order of

```
|S_core|  ≈  N · N · ( Σ_{k=0}^{B_max} C(N, k) ) · (max_moves + 1)
```

For the default board (N = 25, B_max = 5, max_moves = 25):

```
Σ_{k=0}^{5} C(25,k) = 1 + 25 + 300 + 2300 + 12650 + 53130 = 68 406
|S_core| ≈ 25 · 25 · 68 406 · 26 ≈ 1.11 × 10^9   (about a billion configurations)
```

This is already large for a "5×5 toy", and it is **dwarfed** by the message ledger:

### 4.2 The communication state is unbounded

`msg_ledger` is a sequence of **free natural-language strings**. Over a horizon of up to 25
turns × 2 agents, the ledger holds up to ~50 messages, each drawn from the (practically
unbounded) space of natural-language utterances. Formally the message component makes **|S|
countably infinite** (or, if we cap message length at L tokens over a vocabulary V, astronomically
large: |messages| ≤ |V|^L per turn).

**This is the whole point.** The *positional* sub-state is a tractable ~10⁹; the *communication*
sub-state is effectively infinite and is where the orchestration difficulty — and the grade —
actually lives. A numeric protocol would collapse the communication state into a handful of
symbols; **free natural language deliberately does not**, which is why interpreting it requires an
LLM and why mutual understanding cannot be assumed (§7, §9).

---

## 5. {A_i} — the per-agent action sets

Each agent's action on its turn is a **pair**: a *movement/board action* and a *natural-language
message*. We write `a_i = (move_i , msg_i)`.

### 5.1 Movement / board actions

With `allow_diagonal = true` (config), the movement action set on an interior cell is the
**8-neighbourhood plus stay**:

```
A_move = { N, NE, E, SE, S, SW, W, NW, STAY }   (9 actions; 8 directional + stay)
```

- **Both agents** share `A_move`.
- **The Cop additionally** has the action **`PLACE_BARRIER(cell)`** for an eligible target cell
  (typically adjacent), permitted only while `|B| < max_barriers`. This makes the cop's action
  set strictly larger than the thief's — the **capability asymmetry** of the roles.
- A move is **legal** only if the destination cell is in-bounds and **not** in the barrier set
  `B` (see P, §6). Illegal selections are *attempted* actions that the transition turns into
  no-ops; the action space itself is the full 8+stay set, while the *legal* subset is
  state-dependent (`game/moves.py: legal_moves`).

If `allow_diagonal` were set false in config, `A_move` would contract to the
4-neighbourhood + stay; the formalism is unchanged. This is precisely why nothing is hardcoded
(E8): the action set is a function of config.

### 5.2 The communication action

Every turn, each agent also emits **`msg_i` — a free natural-language string** (E4). This is a
genuine action in the Dec-POMDP: it does not change the board, but it **becomes part of the next
state** (`msg_ledger`) and therefore enters the *opponent's* observation `Ω_other` on the
opponent's following turn (via `O`, §7). Messages may:

- **inform** ("I'm boxed against the north wall, two cells east of where I started"),
- **probe** ("Are you near the center? I haven't seen movement on the west side"),
- **bluff / deceive** ("I've already slipped past you toward the south-east corner" — when the
  thief is in fact in the north), or
- **coordinate meta-state** (in the bonus, agreeing on the canonical result framing).

Because `msg_i` is unconstrained text, the *communication action space is effectively infinite*
(§4.2). Crucially, the message is **not** a numeric coordinate handoff; the model forbids a rigid
protocol so that interpretation must be done by the receiving agent's LLM from language alone.

> **Mapping to MCP tools.** `move_i` is realized by the `apply_move(role, direction)` tool (and
> `place_barrier(role, cell)` for the cop); `msg_i` is realized by `send_message(role, content)`,
> and the opponent reads it via `receive_messages()`. The orchestrator chooses the action by
> asking the LLM; the **server only executes** the chosen tool (E3).

---

## 6. P — the transition function (deterministic)

**P(s' | s, a_cop, a_thief)** gives the next state. In this game the board transition is
**fully deterministic** — there is no environmental stochasticity in movement; the only
"randomness" in a run comes from the LLM's choices, which are *agent policy*, not *world dynamics*.

Within a turn the **turn order is `thief → cop`** (config: `turn_order: ["thief","cop"]`; the
**thief moves first**). The transition resolves as:

1. **Thief move.** If the thief's chosen direction leads to an in-bounds, non-barrier cell, the
   thief moves there; otherwise the move is a **no-op** (thief stays put). *(Capture cannot be
   triggered by the thief — only the cop captures.)*
2. **Cop move / barrier.** The cop either (a) moves to an in-bounds, non-barrier cell (illegal →
   no-op), or (b) places a barrier on an eligible cell if `|B| < max_barriers`, which adds that
   cell to `B` and is impassable to both thereafter.
3. **Counter.** `t ← t + 1`.
4. **Messages.** `msg_thief` and `msg_cop` are appended to `msg_ledger`.

### 6.1 The no-op rule (blocked moves)

The single most important transition detail: **blocked moves are no-ops, not errors.** An attempt
to step out of bounds, into a barrier, or (for the thief) into the cop in a way the rules forbid,
leaves the mover where it was and consumes the turn. This keeps the transition **total** (defined
for every (state, action) pair) and means an agent that mis-reasons about geometry simply *wastes a
move* — a natural penalty that the pursuit dynamics impose without special-casing.

### 6.2 Determinism, formally

For all reachable `s` and all joint actions, P assigns probability **1** to exactly one successor
`s'`. The state-machine in `game/` is the canonical implementation of P; because P is
deterministic and config-driven, the **game logic is exhaustively unit-testable** (Phase 2,
coverage ≥ 90% on `game/`) with **no** LLM/MCP/network in the suite (rule 6). Determinism of P is
what lets the bonus produce **byte-identical result JSON** between groups (E12) when fed the same
move sequence.

---

## 7. {Ω_i} and O — partial observability

This is the heart of the **PO** in Dec-POMDP and the formal statement of E4.

### 7.1 Ω_i — each agent's local observation space

A role's observation **ω_i ∈ Ω_i** at its decision point is:

```
ω_i = ( own_pos , vision_cells , known_barriers , t , opponent_last_message )
```

| Field | Content | Notably **absent** |
|---|---|---|
| `own_pos` | the agent's own exact cell. | — |
| `vision_cells` | the contents (empty / barrier / opponent-present) of cells **within a vision radius** of `own_pos`. | the opponent's cell if it lies **outside** the vision radius. |
| `known_barriers` | barrier cells the agent is aware of. | — |
| `t` | the shared move counter. | — |
| `opponent_last_message` | the **free natural-language** message the opponent emitted last turn. | the opponent's *true* coordinates — language only. |

The critical invariant: **ω_i never contains `pos_opponent` directly** unless the opponent
happens to be inside the agent's vision radius (i.e., is *seen*). Outside vision, the *only*
signal about the opponent is **natural language** — which may be incomplete, ambiguous, or
deceptive.

### 7.2 O — the observation function

**O(ω_i | s, i)** deterministically projects the global state to role `i`'s partial view:

- it reveals `own_pos`, the vision-radius window around it, `known_barriers`, and `t`;
- it appends the opponent's most recent ledger message;
- it **redacts** the opponent's exact position whenever the opponent is outside the vision window.

`O` is implemented by the MCP tool **`get_local_observation(role)`**, which lives on the *server*
and is the *only* sanctioned way an agent perceives the world. The server is responsible for the
redaction — this is exactly why "the MCP server holds no secret game-truth beyond what a tool
legitimately exposes": the tool *is* the observation function `O`, and it is unit-tested to assert
the opponent's exact cell is **not** leaked (Phase 3 tests).

### 7.3 Belief state

Because `O` hides the opponent's location, each agent must act on a **belief** `b_i` — a
distribution over the opponent's possible cells — rather than the true state. The agent's belief
is updated each turn from two sources:

1. **geometric evidence** (did the opponent appear in my vision window? did a barrier I placed
   constrain where they could be?), and
2. **linguistic evidence** — the opponent's natural-language message, *interpreted* (and
   *discounted for possible deception*) by the agent's LLM.

The agent's policy maps its **belief + observation history** to an action — the defining signature
of a Dec-POMDP policy `π_i : (ω_i^0, …, ω_i^t) ↦ a_i`. There is **no** policy with access to `s`.

---

## 8. R and γ — rewards and discount

### 8.1 R — the scoring table as a reward function

The reward is **terminal** and **role-asymmetric**, taken verbatim from the spec scoring table
(config `scoring:`). A sub-game ends in exactly one of two terminal events:

| Terminal event | Trigger | Cop reward | Thief reward |
|---|---|---|---|
| **Capture** | the cop **lands on the thief's cell** (`pos_cop == pos_thief`) at or before `t = max_moves`. | **+20** (`cop_win`) | **−5** (`thief_loss`) |
| **Survival** | the move limit is reached (`t = max_moves = 25`) with no capture. | **−5** (`cop_loss`) | **+10** (`thief_win`) |

Intermediate steps carry **reward 0** (the model is sparse-reward: outcome only). The asymmetry
(capture is worth more to the cop, +20, than survival is to the thief, +10) reflects the spec's
intent that the pursuer's success is the harder, higher-value event.

A full **game** is **6 sub-games** (`num_games = 6`); the game score is the **sum** of the
per-sub-game rewards per role, reported in the internal-game JSON `totals{cop, thief}` (E7). The
spec's per-game bounds (max 90 = 6×... / min 30) follow directly from this table.

### 8.2 γ — the discount factor

The horizon is **finite and short** (≤ 25 moves per sub-game), so we use **γ = 1** (no
discounting) for the *game-theoretic* reward: a capture on move 25 is worth the same +20 as a
capture on move 1. This is the correct choice for a finite-horizon, terminal-reward task.

> *Optional learning extension.* If the **Q-Table** (E9, optional per spec §8) is used to produce
> the learning-curve graph (E11), it employs a discount **γ_RL ∈ (0,1)** (a config hyper-parameter)
> in the Bellman update `Q ← Q + α·(r + γ_RL·max_a' Q' − Q)`. This `γ_RL` is an *algorithmic*
> discount internal to the learner and is **distinct** from the game's reward discount γ = 1; it
> exists only to make temporal-difference bootstrapping well-behaved over episodes.

### 8.3 Technical-Loss is outside R (E13)

A sub-game that fails *technically* (an MCP/network/transport fault, not a game outcome) is **not**
scored by R. It is **voided and re-run** so that the game always accumulates **6 valid sub-games**.
In Dec-POMDP terms a Technical-Loss is an *aborted trajectory*, never a terminal reward — the
runner discards it and samples a fresh episode.

---

## 9. Why this is a *genuine* Dec-POMDP coordination problem

It would be easy to dismiss a 5×5 chase as trivial. It is not, once partial observability and
free-language communication are taken seriously — and those two together are exactly what the
assignment grades.

1. **No agent can solve the game alone from its observation.** With `O` redacting the opponent's
   cell, the optimal action depends on the *belief* over the hidden opponent, which can only be
   sharpened by **communication**. A cop with a perfect heuristic but no ability to interpret the
   thief's messages is blind outside its vision radius; the heuristic operates on an **estimate**,
   not ground truth (PRD_strategy makes this explicit).

2. **The communication channel is free natural language, so understanding is not guaranteed.**
   In a classical Dec-POMDP with communication, the message alphabet is finite and its semantics
   are fixed by construction. Here the alphabet is **natural language** and the semantics are
   **emergent**: the sender chooses how to phrase intent, location hints, or bluffs, and the
   receiver's LLM must *infer* meaning under ambiguity. This injects two difficulties absent from
   textbook Dec-POMDPs:
   - **linguistic ambiguity** — "near the corner" must be resolved to a region of cells; and
   - **strategic deception** — a message may be *deliberately false* (the thief bluffing about its
     direction), so the receiver must weigh credibility, not just parse content.

3. **Messaging is an action that shapes the other agent's observation.** This closes the
   Dec-POMDP loop: agent i's choice of `msg_i` at turn t changes `Ω_other` at turn t+1, which
   changes the other's belief, which changes its action, which changes the global state. The
   agents are coupled **through language**, not just through the board — which is precisely the
   *orchestration* the course is about.

4. **Decentralization is enforced architecturally.** The two reasoning contexts (cop, thief) are
   separate LLM calls in the orchestrator (E3); they share **no** hidden variables, only what the
   tools expose. There is no joint controller. This is what makes the problem *decentralized* in
   the strict Dec-POMDP sense rather than a single POMDP solved centrally.

5. **It must run autonomously, end-to-end, over the public internet.** The Dec-POMDP is executed
   by an orchestrator that drives both agents through their MCP servers (local → cloud, E6),
   without human intervention (E5), and emits a JSON report (E7). The formal model is not an
   analysis on paper; it is the live contract the autonomous pipeline satisfies.

In short: **partial observability makes belief necessary; free language makes communication
necessary and unreliable; decentralization makes coordination a non-trivial protocol problem.**
That triad is the genuine Dec-POMDP coordination challenge — and it is the graded substance of
HW6.

---

## 10. What the model forces the code to do (tuple → module map)

| Tuple element | Realized by | Acceptance |
|---|---|---|
| **n = 2** (cop, thief) | `agents/base.py` → `CopAgent`, `ThiefAgent` (role-specific framing). | E4 |
| **S** (state) | `game/state.py` — the serializable `GameState` (positions, barriers, counter, messages). | E1, E8 |
| **{A_i}** moves (+ barrier for cop) | `game/moves.py: legal_moves / apply_move / place_barrier`; tools `apply_move`, `place_barrier`. | E1, E2 |
| **{A_i}** message | tool `send_message(role, content)`; the LLM authors the free-language text. | E4 |
| **P** (deterministic, no-op on blocked) | `game/moves.py` + `game/rules.py` (turn order, no-op rule). | E1 |
| **R** (scoring table) | `game/rules.py` reads `scoring:` from config; totals in `report/output.py`. | E1, E7, E8 |
| **{Ω_i}, O** (partial obs, no leak) | tool `get_local_observation(role)` on the **server** (redaction enforced + tested). | E4, E2, E3 |
| **γ = 1** (finite horizon) | `game/match.py` (sub-game ≤ 25 moves, terminal reward). Optional `γ_RL` in `strategy/qtable.py`. | E1, E9 |
| **belief / NL interpretation** | the per-role LLM prompt in `orchestrator/` consumes `opponent_last_message` and reasons about position + credibility. | E3, E4 |
| **Technical-Loss = voided trajectory** | `orchestrator/runner.py` (void + rerun to 6 valid sub-games). | E13 |

> **Boundary the model enforces (E3).** `O` (`get_local_observation`) and P (`apply_move`,
> `place_barrier`) live on the **MCP servers**; the **policy** (belief update + action choice +
> message authoring) lives **only** in the orchestrator's LLM call. The server never imports or
> calls an LLM. The Dec-POMDP's *dynamics and observation functions* are server-side; the
> *decentralized policies* are client-side. Keeping that split is exactly the Server/Client
> separation the spec grades.

---

## 11. Summary

The COSMOS77-ex06 Cops & Robbers pursuit is a **two-agent, role-asymmetric, communicative
Dec-POMDP** with:

- **n = 2** (cop pursuer, thief evader);
- a **state** S = (cop pos, thief pos, barrier set, move counter, message ledger), whose
  positional core is ≈ 10⁹ configurations on the default board and whose communication component is
  effectively **infinite** because messages are free natural language;
- **actions** {A_i} = 8 directions + stay (+ barrier placement for the cop), each paired with a
  **free natural-language message**;
- a **deterministic transition** P in which blocked moves are no-ops and the thief moves first;
- a **terminal reward** R from the spec scoring table (cop_win 20 / thief_loss 5 ; thief_win 10 /
  cop_loss 5);
- **partial observation** spaces {Ω_i} and an observation function **O** (`get_local_observation`)
  that reveal only own position, a vision-radius window, known barriers, the counter, and the
  opponent's **last NL message** — never the opponent's exact cell;
- a finite-horizon **discount γ = 1**.

The model is *genuinely* decentralized and partially observable: each agent acts on a **belief**
refined through **free-language communication that may be ambiguous or deceptive**, with no central
controller and no shared hidden state. That coordination-under-uncertainty problem — not the chase
itself — is the orchestration the assignment rewards, and this tuple is the formal contract the
autonomous MCP pipeline is built to satisfy (feeds the Phase 10 scientific README, E11).
