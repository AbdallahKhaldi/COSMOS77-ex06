"use strict";
const $ = (id) => document.getElementById(id);
let evtSource = null;
let grid = [5, 5];

async function loadInfo() {
  try {
    const d = await (await fetch("/api/our-info")).json();
    $("our-cop").textContent = d.cop_url || "(not deployed yet)";
    $("our-thief").textContent = d.thief_url || "(not deployed yet)";
  } catch (e) { /* leave placeholders */ }
}

document.querySelectorAll(".copy").forEach((b) =>
  b.addEventListener("click", () => {
    const text = $(b.dataset.target).textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(text);
    b.textContent = "Copied!";
    setTimeout(() => (b.textContent = "Copy"), 1200);
  }));

function drawBoard(rows, cols, cop, thief, barriers) {
  const board = $("board");
  board.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
  board.innerHTML = "";
  const bset = new Set((barriers || []).map((b) => b[0] + "," + b[1]));
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      if (cop && cop[0] === r && cop[1] === c) { cell.classList.add("cop"); cell.textContent = "🚔"; }
      else if (thief && thief[0] === r && thief[1] === c) { cell.classList.add("thief"); cell.textContent = "🏃"; }
      else if (bset.has(r + "," + c)) { cell.classList.add("barrier"); cell.textContent = "▦"; }
      board.appendChild(cell);
    }
  }
}

function addBanter(role, message, flagged) {
  const div = document.createElement("div");
  div.className = "bubble " + (role === "cop" ? "cop" : "thief");
  const who = document.createElement("b");
  who.textContent = (role === "cop" ? "🚔 Cop" : "🏃 Thief") + ": ";
  div.appendChild(who);
  div.appendChild(document.createTextNode(message || ""));
  if (flagged) {
    const warn = document.createElement("span");
    warn.className = "warn";
    warn.textContent = " ⚠ coord leak";
    div.appendChild(warn);
  }
  const box = $("banter");
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function setStatus(msg, cls) {
  const s = $("status");
  s.textContent = msg;
  s.className = "status " + (cls || "");
}

function showResult(ev) {
  const r = ev.result || {};
  if (ev.mode === "exhibition") {
    const w = r.winner === "cop" ? "🚔 Cop wins (capture)" : "🏃 Thief wins (escape)";
    setStatus(`Final: ${w} — cop ${r.cop_score} / thief ${r.thief_score} in ${r.moves} moves`, "done");
  } else {
    const t = r.totals_by_group || {};
    const parts = Object.keys(t).map((k) => `${k}: ${t[k]}`).join("  ·  ");
    setStatus(`Series complete — ${parts}` + (r.path ? `  ·  JSON saved: ${r.path}` : ""), "done");
  }
}

function handleEvent(ev) {
  if (ev.type === "meta") {
    grid = ev.grid || [5, 5];
    drawBoard(grid[0], grid[1], null, null, []);
    $("banter").innerHTML = "";
    setStatus("Running " + ev.mode + " — agents are talking over MCP…", "running");
  } else if (ev.type === "turn") {
    drawBoard(grid[0], grid[1], ev.cop_pos, ev.thief_pos, ev.barriers);
    addBanter(ev.role, ev.message, ev.coord_flagged);
    $("scorebar").textContent = `sub-game ${ev.sub_game} · turn ${ev.turn}` +
      (ev.captured ? "  ·  🚔 CAPTURE!" : "");
  } else if (ev.type === "game_end") {
    showResult(ev);
  } else if (ev.type === "error") {
    setStatus("Error: " + ev.message, "error");
  } else if (ev.type === "done") {
    if (evtSource) { evtSource.close(); evtSource = null; }
  }
}

async function startRun(action) {
  if (evtSource) { evtSource.close(); evtSource = null; }
  setStatus("Starting…", "running");
  const body = {
    action,
    their_cop_url: $("their-cop").value.trim(),
    their_thief_url: $("their-thief").value.trim(),
    token: $("token").value,
    passphrase: $("passphrase").value,
    role: (document.querySelector("input[name=role]:checked") || {}).value || "our_cop",
  };
  let res;
  try {
    res = await (await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })).json();
  } catch (e) { setStatus("Network error reaching the console.", "error"); return; }
  if (res.error) { setStatus(res.error, "error"); return; }
  evtSource = new EventSource("/api/events/" + res.run_id);
  evtSource.onmessage = (m) => { try { handleEvent(JSON.parse(m.data)); } catch (e) { /* skip */ } };
}

$("run-exhibition").addEventListener("click", () => startRun("exhibition"));
$("run-series").addEventListener("click", () => startRun("series"));
loadInfo();
