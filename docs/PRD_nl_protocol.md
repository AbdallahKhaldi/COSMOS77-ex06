# PRD — Free Natural-Language Messaging Protocol (E4)

> **Scope.** This document specifies the *free natural-language* communication
> mechanism between the two autonomous agents (Cop and Thief) in COSMOS77-ex06.
> This is the single most grade-rewarding mechanism of the assignment: the grade
> is the **orchestration** — two autonomous agents coordinating in **free natural
> language** under **partial observability** over **MCP servers** — *not* the game
> strategy. Maps directly to acceptance criterion **E4** (free natural-language
> communication, no rigid numeric protocol; agents infer the opponent's position
> from text) and feeds **E11** (the Dec-POMDP write-up and example transcripts).

---

## 1. Purpose and the one absolute rule

Each turn, an agent emits **one free-text message** to the other agent. The message
is unconstrained prose authored by the agent's LLM (Gemini, living in the
orchestrator / MCP Client per **E3**). It may convey:

- **intentions** ("I'm cutting across to the western wall, you won't reach the corner first"),
- **local observations** ("nothing moved in the cells I can see this turn"),
- or **deliberate deception / bluffing** ("I just spotted you two steps north — I'm closing in").

The receiving agent's LLM **reads and interprets** that message in natural language
and uses it to update its **belief / estimate** of the opponent's position under
partial observability. The interpretation is *also* free reasoning by the LLM — no
parser, no regex, no grammar.

### The one absolute rule (the E4 anti-pattern)

> **Never pass raw coordinates.** No `(x,y)`, no `[3,4]`, no "row 3 col 4", no
> compass-and-distance code, no JSON, no fixed numeric protocol of any kind in the
> agent-to-agent message channel. A message that smuggles coordinates is a
> protocol violation and fails E4.

This is enforced both at the **prompt level** (system instruction forbids it) and by
a **lightweight guard** in the transcript pipeline (see §7) that flags
coordinate-shaped tokens so we can prove, from the logs, that the channel carried
genuine language and not a disguised numeric protocol. The grade rewards messages
that a human reader would recognize as natural English between two players who
*cannot see each other*, where position knowledge is *inferred*, never *transmitted*.

---

## 2. Where this sits in the architecture (Server/Client separation, E3)

```
┌──────────────────────────── ORCHESTRATOR (MCP Client) ────────────────────────────┐
│   GameEngine (turn loop)                                                            │
│   ├─ ThiefAgent.think()  ─► Gemini ─► { nl_message, tool_action }                   │
│   └─ CopAgent.think()    ─► Gemini ─► { nl_message, tool_action }                   │
│                                                                                     │
│   The LLM lives HERE. Belief update, ambiguity handling, deception generation       │
│   and deception detection are all LLM reasoning performed in the client.            │
└───────────────┬───────────────────────────────────────────────┬────────────────────┘
                │ MCP tool calls (token auth)                     │ MCP tool calls
        ┌───────▼────────┐                               ┌────────▼───────┐
        │  COP FastMCP   │                               │ THIEF FastMCP  │
        │  server        │                               │ server         │
        │  TOOLS ONLY:   │                               │  TOOLS ONLY:   │
        │  send_message  │  ◄── message bus / mailbox ──► │  send_message  │
        │  receive_msgs  │                               │  receive_msgs  │
        │  get_local_obs │                               │  get_local_obs │
        │  apply_move …  │                               │  apply_move …  │
        └────────────────┘                               └────────────────┘
```

**Critical boundary (E3):** the natural-language message is *generated* and
*interpreted* by the LLM **in the orchestrator**. The MCP servers are dumb transport:
`send_message(role, content)` deposits an opaque string into the shared mailbox, and
`receive_messages()` returns the opponent's last opaque string. The server never reads,
parses, scores, or understands the message, and it holds **no LLM**. The message is a
free string in → free string out; all *meaning* is produced client-side.

The servers also expose `get_local_observation(role)`, which returns **only** the
partial view that role is entitled to (own position + cells within a vision radius),
and explicitly **does not** leak the opponent's exact cell. This is what makes the
language channel load-bearing: an agent's *only* extra signal about the unseen
opponent is what the opponent *chooses to say* (truth or bluff).

---

## 3. Tie to the Dec-POMDP observation model

The pursuit is formally a **Dec-POMDP** ⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩ (full
treatment in `docs/PRD_dec_pomdp.md`; here we connect the language channel to it).

- **n = 2** decision-makers (Cop, Thief).
- **S** = joint world state = (cop position, thief position, barrier set, move index).
- **Ωᵢ** = agent *i*'s observation space. Each agent observes **only** its own position
  plus a local vision window (and the static barriers it can see) — never the
  opponent's exact cell. This is the **partial observability** that the whole
  exercise turns on.
- **O** = observation function. In a *plain* Dec-POMDP, `O` is fixed by the
  environment. Here we **augment** the effective observation each agent receives with
  the **free-text message** emitted by the other agent. So agent *i*'s realized
  observation each turn is:

  > `oᵢ = ⟨ local_view_from_get_local_observation(i), nl_message_from_opponent ⟩`

  The local view is **trustworthy** (it comes from the MCP server's ground truth,
  filtered to a partial window). The natural-language part is **untrustworthy** — it is
  whatever the opponent decided to author and may be true, vague, or an outright bluff.

- **Belief state bᵢ.** Because the opponent's cell is hidden, each agent maintains an
  *implicit* belief — a distribution / estimate over where the opponent is. The agent
  does **not** maintain an explicit numeric posterior; instead the LLM carries a
  natural-language belief ("probably hugging the eastern columns, was near the top last
  I heard") that it refines turn by turn. Each incoming message is a (noisy, possibly
  adversarial) **observation** that the LLM uses to perform an informal **Bayesian-style
  update**: combine the prior belief, the agent's own local view, the physics of the
  board (reachability in one move, barriers), and the credibility of the message.

This is the scientific framing the README (E11) will use: the message channel is an
**additional, strategically-controlled observation signal** layered on top of the
environment's partial observation function — and because the sender controls it, it is
the locus of **deception** and the reason **mutual understanding** is non-trivial.

---

## 4. The message lifecycle (one turn)

The Thief moves first each turn (`turn_order: ["thief", "cop"]`), then the Cop.
A single agent's turn proceeds:

1. **Sense.** Orchestrator calls `get_local_observation(role)` → the partial view.
2. **Read.** Orchestrator calls `receive_messages()` → the opponent's last free-text
   message (or "no message yet" on turn 0).
3. **Reason (LLM, in the client).** The agent's prompt assembles: role framing,
   current local view, the running belief about the opponent, the opponent's latest
   message, and the move budget left. The LLM is instructed to:
   - (a) **interpret** the incoming message and *update its estimate* of the opponent's
     position (explicitly weighing whether the message is likely truthful or a bluff),
   - (b) **author its own free-text message** (which may itself be honest, vague, or a
     deliberate bluff), and
   - (c) **choose a game action** (a move direction, or for the Cop a barrier placement)
     via an MCP tool.
4. **Speak.** Orchestrator calls `send_message(role, content)` with the authored prose.
5. **Act.** Orchestrator calls `apply_move(role, direction)` (or `place_barrier`).
6. **Log.** The turn record — local view, incoming message, the agent's *interpretation*
   and *updated estimate*, the outgoing message, the chosen action, and the resulting
   board — is appended to the transcript (this transcript is graded evidence for E4/E11).

The LLM returns a small structured envelope to the orchestrator **internally**
(`{ "message": <free text>, "estimate": <free text rationale>, "action": <tool call> }`).
The `estimate` field is the agent's private belief reasoning — it is logged for the
write-up but is **never** sent to the opponent. Only `message` crosses the wire, and it
is free prose. (Note: this internal envelope is orchestrator-side bookkeeping; it is
*not* the agent-to-agent protocol, so it does not violate the "no rigid protocol" rule —
the *channel between agents* carries only `message`, which is unconstrained text.)

---

## 5. Handling linguistic ambiguity

Free language is inherently ambiguous, and we treat ambiguity as a feature to be
*managed*, not a bug to be eliminated.

### 5.1 Sources of ambiguity

- **Vagueness.** "I'm somewhere near the top." (Which columns? How near?)
- **Relative / deictic reference.** "I'm right behind you." (Behind from whose frame?)
- **Underspecification.** "Heading for open space." (There may be several open regions.)
- **Strategic vagueness.** A deliberately fuzzy message that reveals little while
  appearing cooperative.

### 5.2 How we handle it

1. **Interpret against the board physics, not just the words.** The interpreting LLM is
   given its own local view and the rules (one-step reachability, diagonal moves,
   barrier positions). It is instructed to map vague phrases onto the *feasible set of
   cells consistent with the message and the dynamics* — e.g., "near the top" plus "I
   couldn't have crossed the western barrier" narrows the estimate to a small region.
   Ambiguity collapses against constraints.

2. **Carry an estimate, not a point.** The agent is told to maintain a *region* (a fuzzy
   area) rather than commit to a single cell. A vague message *widens* the estimate; a
   specific or corroborated message *narrows* it. The estimate is updated, never
   overwritten — old beliefs decay as the opponent could have moved (a one-step
   reachability expansion of the prior region each turn, consistent with the transition
   model P).

3. **Cross-check against the trustworthy channel.** Anything in the agent's own
   `get_local_observation` window is ground truth and *overrides* the language channel.
   If the Cop's vision shows the Thief is **not** where the Thief's message implied, the
   contradiction is itself information (the message was a bluff — see §6).

4. **Disambiguate over time, not in one shot.** Because messages are exchanged every
   turn, the agent can resolve ambiguity *across turns*: a sequence of vague messages
   plus the agent's own movement gradually triangulates the opponent. The protocol does
   not need a single message to be precise.

5. **Re-ask via the next message (optional clarification).** An agent may use its own
   outgoing message to *probe* — e.g., the Cop says "I think you're boxed against the
   eastern wall," partly to bait the Thief into a revealing reply or a panicked move. The
   reply (or the move that follows) disambiguates. There is no formal request/response
   handshake; clarification emerges naturally from the dialogue.

---

## 6. Deception: producing it and reasoning about it

Deception is explicitly in-scope (the playbook and spec call out "deception/bluffing").
It exists **because** position is hidden and the only channel to the opponent's belief is
the message the opponent reads.

### 6.1 Producing deception (the sender)

The agent prompt permits — and for the Thief, encourages — **strategic messaging**:

- **The Thief** benefits from *misdirection*: claim to flee one way while moving another,
  feign being cornered to lure the Cop into committing, or stay deliberately vague to
  deny the Cop a usable estimate. The Thief's objective (survive `max_moves`) is served
  by keeping the Cop's belief *wrong or wide*.
- **The Cop** benefits from *intimidation and baiting*: overstate certainty ("I have you
  on the north edge") to push the Thief into a predictable escape, or signal a feint to
  herd the Thief toward a barrier wall the Cop is about to close.

The prompt instructs the LLM that messages need not be truthful, but must remain
*plausible* (a transparently absurd lie is worthless — and an over-specific lie risks
contradicting the opponent's own ground-truth view, instantly burning the liar's
credibility). Deception is generated as ordinary persuasive prose; we do not template it.

> **Important boundary:** deception lives **only** in the *message channel*. The
> **actions** an agent reports to its MCP server (`apply_move`, `place_barrier`) are
> always real — they mutate the true board state. An agent can lie about where it is in
> *words*, but it cannot lie to the *engine* about the move it actually makes. This keeps
> the game well-defined while making the language channel a genuine theater for bluffing.

### 6.2 Reasoning about deception (the receiver)

The interpreting LLM is instructed to treat every incoming message as **possibly
adversarial** and to perform credibility-weighted belief updating:

1. **Consistency check against ground truth.** Does the message contradict what the
   agent can directly see (`get_local_observation`)? A contradiction → the message is a
   bluff → *discount it and infer the opposite intent.*
2. **Consistency check against physics.** Is the claim *reachable*? "I'm in the far
   southeast" when one move ago the opponent was provably near the northwest and only one
   step is possible per turn → physically impossible → bluff.
3. **Consistency check across turns.** Does the message contradict the opponent's own
   earlier statements (without a plausible move bridging them)? Incoherent claims erode
   credibility.
4. **Incentive reasoning.** The LLM is reminded of the opponent's objective: a Thief is
   *motivated* to mislead, so its claims warrant skepticism; a confident Cop claim might
   be a bait. The receiver weights the message by *who benefits if I believe it.*
5. **Don't over-rotate.** The receiver is warned against the symmetric trap of assuming
   *everything* is a lie (paranoia is as exploitable as gullibility). The instruction is
   to keep a **calibrated** belief: take corroborated, physically-plausible,
   incentive-neutral statements at higher weight; discount the rest.

The output of this reasoning is the updated **estimate** (logged), which then drives the
heuristic/Q-Table action selection on the agent's *belief* of the opponent — never on
ground truth it isn't entitled to (see `docs/PRD_strategy.md`: strategy operates on the
*estimate*).

---

## 7. Mutual understanding: how it is checked and maintained

With no fixed protocol, "did we understand each other?" is a real question. We maintain
mutual understanding through several lightweight, *language-native* mechanisms:

1. **Shared, explicit frame of reference in the prompts.** Both agents are told the same
   board conventions in natural language (e.g., "north = toward the top edge / lower row
   index; the grid has a clear top, bottom, eastern and western walls; corners and walls
   are landmarks"). This gives them a *common vocabulary of landmarks* (walls, corners,
   center, barrier lines) so phrases like "the eastern wall" or "the top-left corner"
   denote the same regions for both. Landmarks, not coordinates, are the lingua franca.

2. **Grounding through behavior.** Understanding is verified *implicitly*: if the Cop
   interprets "I'm fleeing to open space" and positions accordingly, and the subsequent
   board state is consistent with that interpretation, mutual understanding held. The
   transcript (move-by-move board + messages) lets us **audit** whether interpretations
   tracked reality.

3. **Conversational repair.** When an agent's belief is contradicted (its own view
   disproves the message, §6.2), it does not crash — it *repairs*: it updates the
   estimate and may call out the discrepancy in its next message ("you said north, but
   you're clearly not — nice try"). The dialogue self-corrects.

4. **Belief continuity.** The agent's running `estimate` is threaded into each prompt, so
   understanding is *cumulative*. A single ambiguous turn does not derail the shared
   picture; it is integrated into an evolving belief.

5. **Transcript-level guard (proof for the grader).** A post-turn check scans each
   outgoing message for coordinate-shaped tokens (e.g., `\d+\s*[,;]\s*\d+`, `row\s*\d`,
   `col\s*\d`, bracketed pairs). A hit is **flagged in the log** (and, in dev, the agent
   is re-prompted to rephrase in landmarks). This both *enforces* the no-numeric-protocol
   rule and *produces evidence* that the channel carried genuine language — exactly what
   E4 is graded on. The guard never edits meaning; it only polices the numeric-leak
   anti-pattern.

These mechanisms are deliberately *not* a handshake or schema. Mutual understanding is an
emergent property of two LLMs sharing a landmark vocabulary, grounding language in
observed board changes, and repairing misunderstandings in subsequent messages — which is
precisely the orchestration challenge the assignment wants demonstrated.

---

## 8. Example message exchanges

The following are illustrative exchanges (the kind the real transcript will contain; the
*shape*, not verbatim Gemini output). Each shows the message on the wire plus the
receiver's private, logged interpretation — note that **no coordinates ever cross the
channel**.

### 8.1 Honest local observation + cautious inference

> **Thief → Cop:** "Quiet over here — I haven't seen anything move in the cells around me
> this turn, so you're not close yet. I'm drifting toward the open middle of the board."
>
> **Cop's private estimate (logged, not sent):** "Thief claims I'm not nearby and is
> heading center. My own view confirms I can't see the Thief, so 'not close' is
> consistent — low bluff risk. 'Open middle' plus the barrier I placed on the western
> column means the feasible region is the central-eastern cells. I'll converge from the
> south to cut the center."
>
> **Cop → Thief:** "I'm working up the southern edge. The middle isn't as open as you
> think — there's a wall of barriers forming on your west."

### 8.2 Thief bluff, caught by ground truth (deception detection)

> **Thief → Cop:** "I just slipped past you on the north side — I'm well behind you now,
> you're chasing a ghost."
>
> **Cop's private estimate (logged):** "My local view this turn clearly shows the
> northern cells beside me are empty — the Thief did *not* pass me there. This is a bluff
> meant to make me wheel north and abandon my line. Discount it. The lie's purpose
> suggests the Thief is actually *south* of me, trying to keep me looking the wrong way.
> I'll hold my southward press and tighten."
>
> **Cop → Thief:** "Cute. Nobody passed me on the north — you're still ahead of me, and
> the gap is closing."

### 8.3 Ambiguity resolved over two turns (triangulation)

> **Turn k — Thief → Cop:** "Hugging a wall, staying out of the center."
> **Cop's estimate:** "Could be any of the four walls — too vague to act decisively. Keep
> a wide belief; I'll probe."
>
> **Turn k — Cop → Thief (probe):** "Smart to hug a wall — though the eastern one is a
> dead end with the barriers I'm placing."
>
> **Turn k+1 — Thief → Cop:** "Not falling for that — plenty of room where I am."
> **Cop's estimate (updated):** "The Thief denied the *eastern* dead-end specifically and
> claims room to move — consistent with being on the *western* or *southern* wall, away
> from my eastern barriers. The earlier vagueness is now narrowed to the west/south
> region. Converge southwest."

### 8.4 Cop feint to herd the Thief (deception by the pursuer)

> **Cop → Thief:** "I'm committing hard to the north — sealing the top two rows. Your only
> air is downward."
>
> **Cop's true plan (logged):** "I am *not* sealing the north; I'm setting a barrier line
> to the south to catch the Thief as it flees 'downward' on my suggestion."
>
> **Thief's private estimate (logged):** "Cop says it's locking the north and pushing me
> down. But a confident, convenient claim from a pursuer is exactly what a bait looks
> like — *who benefits if I flee south?* The Cop does. I'll treat 'go south' as a trap and
> instead break laterally west."

These exchanges demonstrate, for the README and the grader: free prose on the wire;
position **inferred** not transmitted; ambiguity handled via physics + landmarks +
multi-turn triangulation; deception both **produced** (8.2 Thief, 8.4 Cop) and
**reasoned about** (consistency, physics, incentive checks); and mutual understanding
maintained through a shared landmark frame and conversational repair.

---

## 9. Prompt design (orchestrator-side, summary)

The per-turn agent prompt (built in `agents/base.py`, role-specialized in
`CopAgent`/`ThiefAgent`) is assembled from config and live state and instructs the LLM to:

- adopt its **role objective** (Cop: capture within `max_moves`; Thief: survive),
- read the **local observation** (trustworthy, partial) and the **opponent's last
  message** (untrustworthy),
- **interpret** the message and **update its estimate** of the opponent, applying the
  §6.2 credibility checks and the §5 ambiguity handling,
- **author one free-text message** in landmark language (the §7.1 shared frame),
  honest or deceptive as strategy dictates, **with no coordinates** (§1),
- **choose one game action** via an MCP tool, acting on its *estimate*, not on hidden
  ground truth,
- return the internal envelope `{ message, estimate, action }` to the orchestrator.

All knobs (model, temperature, vision radius, board conventions text, the
no-coordinate guard patterns) are **config-driven** (`config/config.yaml`,
CLAUDE.md rule 4 / E8); nothing about the protocol is hardcoded in logic.

---

## 10. Testing the protocol (deterministic, all I/O mocked — rules 6 & 17)

The protocol is exercised with **mocked Gemini and mocked FastMCP clients** — no live
LLM, MCP, or network in the suite. Key assertions:

- **A message is exchanged every turn.** Each turn record has a non-empty `message` field
  for the acting agent.
- **The channel is non-numeric (E4 guard).** Outgoing messages pass the no-coordinate
  check; a fixture message containing `(3,4)` / `row 3 col 4` is flagged by the guard.
- **The LLM is called by the orchestrator, never by the server (E3).** Assert
  `mcp_servers/` imports/calls no LLM; the engine drives the Gemini call.
- **Belief updates on input.** Given a fixture incoming message + a fixture local view,
  the (mocked) agent's logged `estimate` changes from the prior — proving the message is
  consumed, not ignored.
- **Deception detection path.** A fixture where the incoming message contradicts the
  agent's local view yields a logged interpretation that *discounts* the message
  (credibility-check branch covered).
- **Transcript completeness.** Every turn logs local view, incoming message,
  interpretation/estimate, outgoing message, action, and resulting board (the E4/E11
  evidence).

Determinism: seed `random`, fix positions and the mocked LLM responses, mock all I/O.

---

## 11. Acceptance mapping

| Item in this PRD | Acceptance criterion |
|---|---|
| Free-text message each turn; no rigid/numeric protocol; position inferred from text | **E4** |
| LLM generates & interprets messages in the orchestrator; servers are tools-only | **E3** |
| Augmented observation `oᵢ = ⟨local view, opponent message⟩`; belief update under partial obs | **E4**, **E11** (Dec-POMDP) |
| Ambiguity handling, mutual-understanding maintenance, deception produced & detected | **E11** (orchestration-challenge analysis — the section the grade rewards most) |
| Example exchanges drawn from the real transcript | **E11** (NL-protocol section) |
| All protocol knobs in `config/config.yaml`, nothing hardcoded | **E8** |
| Messages flow over the public cloud MCP servers in the full run | **E5**, **E6** |

---

## 12. Open decisions / ADR pointers

- **Clarification handshake?** *Rejected.* No formal request/response. Clarification is
  emergent (§5.4, §5.5) to keep the channel genuinely free-form (ADR in `docs/PLAN.md`).
- **Explicit numeric belief posterior?** *Rejected for the agent channel.* The agent's
  belief is natural-language reasoning; only the *strategy layer* may discretize an
  estimate region internally for move selection (see `docs/PRD_strategy.md`).
- **Re-prompt on a no-coordinate-guard hit?** *Dev only* (re-ask to rephrase in
  landmarks); in scored runs the guard logs/flags so the violation is visible rather than
  silently rewritten.
