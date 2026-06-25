"use strict";
const $ = (id) => document.getElementById(id);
let ws = null;
const G = { rows: 5, cols: 5, vision: 1, maxMoves: 25, numGames: 1, mode: "house" };

/* ---------- our coordinates ---------- */
async function loadInfo() {
  try {
    const d = await (await fetch("/api/our-info")).json();
    $("our-cop").textContent = d.cop_url || "(servers offline — run deploy/live_tunnels.sh)";
    $("our-thief").textContent = d.thief_url || "(servers offline)";
  } catch (e) { /* keep placeholder */ }
}

/* ---------- mode tabs ---------- */
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    const house = t.dataset.mode === "house";
    $("panel-house").classList.toggle("hidden", !house);
    $("panel-challenge").classList.toggle("hidden", house);
  }));

/* ---------- settings sliders ---------- */
function wireSlider(id, out, fmt) {
  const el = $(id), o = $(out);
  const upd = () => { o.textContent = fmt(el.value); };
  el.addEventListener("input", upd); upd();
}
wireSlider("set-grid", "grid-val", (v) => v + "×" + v);
wireSlider("set-moves", "moves-val", (v) => v);
wireSlider("set-games", "games-val", (v) => v);

/* ---------- board geometry ---------- */
function buildGrid() {
  const grid = $("grid");
  grid.style.gridTemplateColumns = `repeat(${G.cols},1fr)`;
  grid.style.gridTemplateRows = `repeat(${G.rows},1fr)`;
  grid.innerHTML = "";
  for (let i = 0; i < G.rows * G.cols; i++) {
    const c = document.createElement("div");
    c.className = "cell";
    grid.appendChild(c);
  }
}
function sizeBoard() {
  const usable = $("board").clientWidth * 0.88;
  const cell = usable / G.cols;
  const tk = cell * 0.8;
  document.querySelectorAll(".token").forEach((t) => {
    t.style.width = tk + "px"; t.style.height = tk + "px"; t.style.fontSize = tk * 0.6 + "px";
  });
  const vs = cell * (2 * G.vision + 1) * 0.92;
  ["vis-cop", "vis-thief"].forEach((id) => { $(id).style.width = vs + "px"; $(id).style.height = vs + "px"; });
}
function place(el, row, col) {
  el.style.left = ((col + 0.5) / G.cols) * 100 + "%";
  el.style.top = ((row + 0.5) / G.rows) * 100 + "%";
}
function trail(role, row, col) {
  const d = document.createElement("div");
  d.className = "trail " + role;
  place(d, row, col);
  $("overlay").appendChild(d);
  setTimeout(() => d.remove(), 1100);
}
window.addEventListener("resize", sizeBoard);

function idleBoard() {
  G.rows = 5; G.cols = 5; G.vision = 1; G.maxMoves = 25;
  buildGrid(); sizeBoard(); buildPips(1);
  place($("tok-cop"), 4, 4); place($("vis-cop"), 4, 4);
  place($("tok-thief"), 0, 0); place($("vis-thief"), 0, 0);
  $("movereadout").textContent = "standby";
  const f = $("feed");
  if (!f.children.length) {
    const s = document.createElement("div");
    s.className = "bubble sys";
    s.textContent = "// comms channel open — awaiting engagement";
    f.appendChild(s);
  }
}

/* ---------- labels per mode ---------- */
function setLabels(mode) {
  const map = {
    house: ["COSMOS77", "COSMOS77"],
    match: ["COSMOS77", "RIVAL"],
    swap: ["RIVAL", "COSMOS77"],
    series: ["ROLE-SWAP · 6", "ROLE-SWAP · 6"],
  };
  const [ct, tt] = map[mode] || map.house;
  $("cop-team").textContent = ct;
  $("thief-team").textContent = tt;
}

/* ---------- comms ---------- */
function addComms(role, message, flagged) {
  const b = document.createElement("div");
  b.className = "bubble " + (role === "cop" ? "cop" : "thief");
  const who = document.createElement("b");
  who.textContent = role === "cop" ? "🚔 DETECTIVE" : "🏃 ROGUE";
  b.appendChild(who);
  b.appendChild(document.createTextNode(message || ""));
  if (flagged) {
    const f = document.createElement("span");
    f.className = "flag"; f.textContent = "⚠ COORD LEAK";
    b.appendChild(f);
  }
  const feed = $("feed");
  feed.appendChild(b);
  feed.scrollTop = feed.scrollHeight;
}

/* ---------- subgame pips ---------- */
function buildPips(n) {
  const p = $("subpips"); p.innerHTML = "";
  for (let i = 0; i < n; i++) p.appendChild(document.createElement("i"));
}
function markPip(idx) {
  const pips = $("subpips").children;
  for (let i = 0; i < pips.length; i++) pips[i].classList.toggle("now", i === idx - 1);
}

/* ---------- status ---------- */
function status(text, live) {
  $("statustext").textContent = text;
  $("ping").classList.toggle("live", !!live);
}

/* ---------- event handling ---------- */
function onMeta(e) {
  G.rows = e.grid[0]; G.cols = e.grid[1];
  G.vision = e.vision_radius || 1; G.maxMoves = e.max_moves || 25;
  $("arena").classList.remove("hidden");
  $("verdict").classList.add("hidden"); $("newmatch").classList.add("hidden");
  $("feed").innerHTML = ""; $("leakwarn").textContent = "";
  $("cop-score").textContent = "0"; $("thief-score").textContent = "0";
  buildGrid(); sizeBoard();
  G.numGames = e.num_games || (e.mode === "series" ? 6 : 1);
  buildPips(G.numGames);
  place($("tok-cop"), G.rows - 1, G.cols - 1); place($("vis-cop"), G.rows - 1, G.cols - 1);
  place($("tok-thief"), 0, 0); place($("vis-thief"), 0, 0);
  $("movereadout").textContent = "game 1 / " + G.numGames + " · move 0 / " + G.maxMoves;
  status("● LIVE — agents engaging over MCP", true);
  $("arena").scrollIntoView({ behavior: "smooth" });
}
let leaks = 0;
function onTurn(e) {
  const cop = $("tok-cop"), thief = $("tok-thief");
  if (e.role === "cop") { trail("cop", +cop.dataset.r || G.rows - 1, +cop.dataset.c || G.cols - 1); }
  else { trail("thief", +thief.dataset.r || 0, +thief.dataset.c || 0); }
  place(cop, e.cop_pos[0], e.cop_pos[1]); place($("vis-cop"), e.cop_pos[0], e.cop_pos[1]);
  place(thief, e.thief_pos[0], e.thief_pos[1]); place($("vis-thief"), e.thief_pos[0], e.thief_pos[1]);
  cop.dataset.r = e.cop_pos[0]; cop.dataset.c = e.cop_pos[1];
  thief.dataset.r = e.thief_pos[0]; thief.dataset.c = e.thief_pos[1];
  document.querySelector(".agent.cop").classList.toggle("active", e.role === "cop");
  document.querySelector(".agent.thief").classList.toggle("active", e.role === "thief");
  $("vis-" + e.role).classList.remove("pulse"); void $("vis-" + e.role).offsetWidth;
  $("vis-" + e.role).classList.add("pulse");
  (e.barriers || []).forEach((b) => {
    const cell = $("grid").children[b[0] * G.cols + b[1]];
    if (cell) cell.classList.add("barrier");
  });
  addComms(e.role, e.message, e.coord_flagged);
  if (e.coord_flagged) { leaks++; $("leakwarn").textContent = "· " + leaks + " flagged"; }
  markPip(e.sub_game);
  $("movereadout").textContent = "game " + e.sub_game + " / " + G.numGames + " · move " + e.turn + " / " + G.maxMoves;
  if (e.captured) { const l = $("lockon"); l.classList.remove("fire"); void l.offsetWidth; l.classList.add("fire"); }
}
function onSubGameEnd(e) {
  if (e.totals) { $("cop-score").textContent = e.totals.cop; $("thief-score").textContent = e.totals.thief; }
  const pip = $("subpips").children[e.sub_game - 1];
  if (pip) { pip.classList.remove("now"); pip.classList.add(e.winner === "cop" ? "cop" : "thief"); }
}
function onEnd(e) {
  const r = e.result || {};
  const v = $("verdict");
  if (e.mode === "series") {
    const t = r.totals_by_group || {};
    const parts = Object.keys(t).map((k) => k + " " + t[k]).join("  ·  ");
    v.className = "verdict";
    v.textContent = "SERIES COMPLETE";
    const s = document.createElement("small"); s.textContent = parts + (r.path ? "  ·  record saved" : "");
    v.appendChild(s);
    (r.sub_games || []).forEach((sg, i) => {
      const pip = $("subpips").children[i];
      if (pip) pip.classList.add(sg.result === "capture" ? "cop" : "thief");
    });
  } else {
    $("cop-score").textContent = r.cop_score; $("thief-score").textContent = r.thief_score;
    (r.games || []).forEach((g, i) => {
      const pip = $("subpips").children[i];
      if (pip) { pip.classList.remove("now"); pip.classList.add(g.winner === "cop" ? "cop" : "thief"); }
    });
    const win = r.winner, n = r.num_games || 1;
    v.className = "verdict " + (win === "tie" ? "" : win);
    if (n > 1) v.textContent = win === "cop" ? "🚔 DETECTIVE TAKES THE MATCH" : win === "thief" ? "🏃 ROGUE TAKES THE MATCH" : "⚖ DEAD HEAT";
    else v.textContent = win === "cop" ? "🚔 DETECTIVE CAPTURES THE ROGUE" : "🏃 ROGUE ESCAPES";
    const tape = (r.games || []).map((g) => (g.winner === "cop" ? "🚔" : "🏃")).join(" ");
    const s = document.createElement("small");
    s.textContent = tape + "   cop " + r.cop_score + " · thief " + r.thief_score;
    v.appendChild(s);
  }
  v.classList.remove("hidden");
}
function handle(e) {
  if (e.type === "meta") onMeta(e);
  else if (e.type === "turn") onTurn(e);
  else if (e.type === "sub_game_end") onSubGameEnd(e);
  else if (e.type === "game_end") onEnd(e);
  else if (e.type === "error") status("⚠ " + e.message, false);
  else if (e.type === "done") {
    if (ws) { try { ws.close(); } catch (x) { /* */ } ws = null; }
    status("SYSTEM READY", false);
    document.querySelectorAll(".agent").forEach((a) => a.classList.remove("active"));
    $("engage").disabled = false; $("newmatch").classList.remove("hidden");
  }
}

/* ---------- engage ---------- */
async function engage() {
  const mode = document.querySelector(".tab.active").dataset.mode;
  let body = { passphrase: $("passphrase").value };
  if (mode === "house") {
    body.action = "solo"; setLabels("house"); leaks = 0;
  } else {
    const cmode = (document.querySelector("input[name=cmode]:checked") || {}).value || "match";
    body.their_cop_url = $("their-cop").value.trim();
    body.their_thief_url = $("their-thief").value.trim();
    body.token = $("token").value;
    body.action = cmode === "series" ? "series" : "exhibition";
    if (cmode === "swap") body.role = "their_cop";
    setLabels(cmode); leaks = 0;
  }
  body.grid = +$("set-grid").value; body.moves = +$("set-moves").value; body.games = +$("set-games").value;
  $("err").textContent = ""; $("engage").disabled = true; status("authorizing…", false);
  let res;
  try {
    res = await (await fetch("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    })).json();
  } catch (err) { $("err").textContent = "Network error reaching control."; $("engage").disabled = false; return; }
  if (res.error) { $("err").textContent = res.error; $("engage").disabled = false; status("SYSTEM READY", false); return; }
  if (ws) { try { ws.close(); } catch (x) { /* */ } }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(proto + "//" + location.host + "/api/ws/" + res.run_id);
  ws.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (err) { /* skip */ } };
  ws.onerror = () => status("⚠ connection error", false);
}
$("engage").addEventListener("click", engage);
$("newmatch").addEventListener("click", () => {
  if (ws) { try { ws.close(); } catch (x) { /* */ } ws = null; }
  $("verdict").classList.add("hidden");
  $("newmatch").classList.add("hidden");
  $("cop-score").textContent = "0"; $("thief-score").textContent = "0";
  $("feed").innerHTML = "";
  $("leakwarn").textContent = "";
  document.querySelectorAll(".agent").forEach((a) => a.classList.remove("active"));
  setLabels("house");
  idleBoard();
  status("SYSTEM READY", false);
  document.getElementById("setup").scrollIntoView({ behavior: "smooth" });
});
loadInfo();
requestAnimationFrame(idleBoard);
