"use strict";
const $ = (id) => document.getElementById(id);
let ws = null;
const G = { rows: 5, cols: 5, vision: 1, maxMoves: 25, numGames: 1, mode: "house" };

/* ---------- our coordinates ---------- */
async function loadInfo() {
  const set = (ids, txt) => ids.forEach((id) => { const e = $(id); if (e) e.textContent = txt; });
  try {
    const d = await (await fetch("/api/our-info")).json();
    set(["our-cop", "our-cop-2"], d.cop_url || "(servers offline — start the MCP tunnels)");
    set(["our-thief", "our-thief-2"], d.thief_url || "(servers offline — start the MCP tunnels)");
  } catch (e) {
    set(["our-cop", "our-cop-2", "our-thief", "our-thief-2"], "(offline — could not reach control)");
  }
}

/* ---------- mode tabs ---------- */
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => {
      x.classList.remove("active");
      x.setAttribute("aria-selected", "false");
    });
    t.classList.add("active");
    t.setAttribute("aria-selected", "true");
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
/* procedural top-down GTA city behind #grid — roads on cell centres; cars drive the streets */
function _mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};}

/* Build/refresh the top-down city SVG behind #grid for current G.rows x G.cols. */
function buildCity(){
  const board=$("board"), grid=$("grid");
  if(!board||!grid) return;
  let city=board.querySelector(".city");
  if(!city){ city=document.createElement("div"); city.className="city"; board.insertBefore(city,grid); }
  const rows=G.rows,cols=G.cols,V=1000;
  const rand=_mulberry32(rows*131+cols*17+101);
  const cx=(i)=>((i+0.5)/cols)*V, cy=(i)=>((i+0.5)/rows)*V;   // cell centres == road centres (matches place())
  const roadW=Math.max(30,Math.min(118,(V/Math.max(rows,cols))*0.40)), half=roadW/2;
  const s=[];
  const R=(x,y,w,h,f,ex="")=>s.push(`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" fill="${f}" ${ex}/>`);
  s.push(`<svg viewBox="0 0 ${V} ${V}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">`);
  R(0,0,V,V,"#0b0e1a");                                       // ground

  const colE=[];for(let c=0;c<cols;c++)colE.push([cx(c)-half,cx(c)+half]);
  const rowE=[];for(let r=0;r<rows;r++)rowE.push([cy(r)-half,cy(r)+half]);

  // city blocks = rectangles BETWEEN the roads (plus outer margins)
  const blocks=[];
  for(let bc=0;bc<=cols;bc++){
    const x0=bc===0?0:colE[bc-1][1], x1=bc===cols?V:colE[bc][0]; if(x1-x0<6)continue;
    for(let br=0;br<=rows;br++){
      const y0=br===0?0:rowE[br-1][1], y1=br===rows?V:rowE[br][0]; if(y1-y0<6)continue;
      blocks.push({x:x0,y:y0,w:x1-x0,h:y1-y0,bc,br});
    }
  }
  // one park + one water block (prefer interior so they read clearly)
  const interior=blocks.filter(b=>b.bc>0&&b.bc<cols&&b.br>0&&b.br<rows);
  const pool=interior.length?interior:blocks;
  const park=pool[Math.floor(rand()*pool.length)];
  let water=pool[Math.floor(rand()*pool.length)];
  if(water===park)water=pool[(pool.indexOf(park)+1)%pool.length];

  const browns=["#3b3024","#342a20","#2f2922","#403428"];
  const greys=["#2b2e39","#262a35","#31353f","#222530","#363a45"];
  for(const b of blocks){
    if(b===park){                                            // PARK + tree canopies
      R(b.x,b.y,b.w,b.h,"#13351d"); R(b.x,b.y,b.w,b.h,"none",'stroke="#0006" stroke-width="2"');
      const n=3+Math.floor(rand()*5);
      for(let k=0;k<n;k++){const tx=b.x+8+rand()*Math.max(1,b.w-16),ty=b.y+8+rand()*Math.max(1,b.h-16),rr=4+rand()*8;
        s.push(`<circle cx="${tx.toFixed(1)}" cy="${ty.toFixed(1)}" r="${rr.toFixed(1)}" fill="#1f5a30"/>`);
        s.push(`<circle cx="${(tx-rr*0.3).toFixed(1)}" cy="${(ty-rr*0.3).toFixed(1)}" r="${(rr*0.55).toFixed(1)}" fill="#2c7a42"/>`);}
      continue;
    }
    if(b===water){                                           // WATER + ripples
      R(b.x,b.y,b.w,b.h,"#103b54"); R(b.x,b.y,b.w,b.h,"#1d6f96",'opacity="0.35"');
      for(let k=0;k<3;k++){const wy=b.y+b.h*(0.25+0.22*k);
        s.push(`<line x1="${(b.x+6).toFixed(1)}" y1="${wy.toFixed(1)}" x2="${(b.x+b.w-6).toFixed(1)}" y2="${wy.toFixed(1)}" stroke="#9fd8ef" stroke-width="1.5" opacity="0.25"/>`);}
      continue;
    }
    // BUILDING footprint inset within the block
    const pal=rand()<0.42?browns:greys, fill=pal[Math.floor(rand()*pal.length)];
    const pad=Math.min(b.w,b.h)*(0.05+rand()*0.07);
    const x=b.x+pad,y=b.y+pad,w=b.w-2*pad,h=b.h-2*pad;
    if(w<8||h<8){R(b.x,b.y,b.w,b.h,"#1a1a22");continue;}
    R(x,y,w,h,fill,'rx="2"');
    R(x,y,w,h,"none",'rx="2" stroke="#0007" stroke-width="2"');           // dark edge = building height
    R(x+2,y+2,w-4,h-4,"none",'rx="1" stroke="#ffffff10" stroke-width="1.5"'); // roof rim highlight
    const nAC=Math.floor(rand()*3);                          // rooftop AC units / vents
    for(let k=0;k<nAC;k++){const aw=4+rand()*8,ah=4+rand()*8;
      const ax=x+4+rand()*Math.max(1,w-aw-8),ay=y+4+rand()*Math.max(1,h-ah-8);
      R(ax,ay,aw,ah,"#00000038"); R(ax,ay,aw,ah,"none",'stroke="#ffffff14" stroke-width="1"');}
    if(rand()<0.5){const sy=y+h*(0.3+rand()*0.4);            // roof seam
      s.push(`<line x1="${(x+3).toFixed(1)}" y1="${sy.toFixed(1)}" x2="${(x+w-3).toFixed(1)}" y2="${sy.toFixed(1)}" stroke="#ffffff0c" stroke-width="1"/>`);}
  }

  // ROADS (asphalt) over the blocks so junctions stay clean
  for(let r=0;r<rows;r++)R(0,cy(r)-half,V,roadW,"#191b21");
  for(let c=0;c<cols;c++)R(cx(c)-half,0,roadW,V,"#191b21");
  const ce=Math.max(1.5,roadW*0.035);                        // curbs
  for(let r=0;r<rows;r++){R(0,cy(r)-half,V,ce,"#0a0b10");R(0,cy(r)+half-ce,V,ce,"#0a0b10");}
  for(let c=0;c<cols;c++){R(cx(c)-half,0,ce,V,"#0a0b10");R(cx(c)+half-ce,0,ce,V,"#0a0b10");}

  // yellow centre dashes down every street
  const dash=roadW*0.55,gap=roadW*0.75,lw=Math.max(2,roadW*0.05);
  for(let r=0;r<rows;r++)s.push(`<line x1="0" y1="${cy(r).toFixed(1)}" x2="${V}" y2="${cy(r).toFixed(1)}" stroke="#ffd400" stroke-width="${lw.toFixed(1)}" stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}" opacity="0.85"/>`);
  for(let c=0;c<cols;c++)s.push(`<line x1="${cx(c).toFixed(1)}" y1="0" x2="${cx(c).toFixed(1)}" y2="${V}" stroke="#ffd400" stroke-width="${lw.toFixed(1)}" stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}" opacity="0.85"/>`);

  // crosswalks: zebra stripes on all 4 approaches of every intersection
  const nS=4, sw=Math.max(2.5,roadW*0.085), pitch=roadW/(nS+0.5);
  const cwLen=roadW*0.5, near=half+roadW*0.06, far=near+cwLen;
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
    const ix=cx(c),iy=cy(r);
    for(let k=0;k<nS;k++){const off=(k-(nS-1)/2)*pitch;
      s.push(`<line x1="${(ix+off).toFixed(1)}" y1="${(iy-far).toFixed(1)}" x2="${(ix+off).toFixed(1)}" y2="${(iy-near).toFixed(1)}" stroke="#dfe5f0" stroke-width="${sw.toFixed(1)}" opacity="0.5"/>`);
      s.push(`<line x1="${(ix+off).toFixed(1)}" y1="${(iy+near).toFixed(1)}" x2="${(ix+off).toFixed(1)}" y2="${(iy+far).toFixed(1)}" stroke="#dfe5f0" stroke-width="${sw.toFixed(1)}" opacity="0.5"/>`);
      s.push(`<line x1="${(ix-far).toFixed(1)}" y1="${(iy+off).toFixed(1)}" x2="${(ix-near).toFixed(1)}" y2="${(iy+off).toFixed(1)}" stroke="#dfe5f0" stroke-width="${sw.toFixed(1)}" opacity="0.5"/>`);
      s.push(`<line x1="${(ix+near).toFixed(1)}" y1="${(iy+off).toFixed(1)}" x2="${(ix+far).toFixed(1)}" y2="${(iy+off).toFixed(1)}" stroke="#dfe5f0" stroke-width="${sw.toFixed(1)}" opacity="0.5"/>`);
    }
  }
  // vignette so the play area pops
  s.push(`<radialGradient id="cv" cx="50%" cy="46%" r="62%"><stop offset="62%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.45"/></radialGradient>`);
  R(0,0,V,V,"url(#cv)");
  s.push(`</svg>`);
  city.innerHTML=s.join("");   // fully machine-generated from numeric N -> no untrusted input
}

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
    t.style.width = tk + "px"; t.style.height = tk * 1.18 + "px";
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

/* fog-of-war: tint the cells an agent can actually see (Chebyshev vision footprint) */
function markVision(role, row, col) {
  const cls = "scan-" + role;
  document.querySelectorAll(".cell." + cls).forEach((c) => c.classList.remove(cls));
  const cells = $("grid").children;
  for (let r = Math.max(0, row - G.vision); r <= Math.min(G.rows - 1, row + G.vision); r++) {
    for (let c = Math.max(0, col - G.vision); c <= Math.min(G.cols - 1, col + G.vision); c++) {
      const cell = cells[r * G.cols + c];
      if (cell && !cell.classList.contains("barrier")) cell.classList.add(cls);
    }
  }
}

function idleBoard() {
  G.rows = 5; G.cols = 5; G.vision = 1; G.maxMoves = 25;
  buildGrid(); buildCity(); sizeBoard(); buildPips(1);
  place($("tok-cop"), 4, 4); markVision("cop", 4, 4);
  place($("tok-thief"), 0, 0); markVision("thief", 0, 0);
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
  who.textContent = role === "cop" ? "🚓 DETECTIVE" : "🚗 ROGUE";
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
  buildGrid(); buildCity(); sizeBoard();
  G.numGames = e.num_games || (e.mode === "series" ? 6 : 1);
  buildPips(G.numGames);
  place($("tok-cop"), G.rows - 1, G.cols - 1); markVision("cop", G.rows - 1, G.cols - 1);
  place($("tok-thief"), 0, 0); markVision("thief", 0, 0);
  $("movereadout").textContent = "game 1 / " + G.numGames + " · move 0 / " + G.maxMoves;
  status("● LIVE — agents engaging over MCP", true);
  $("arena").scrollIntoView({ behavior: "smooth" });
}
let leaks = 0;
let runActive = false;
let watchdog = null;
function resetWatchdog() {
  if (watchdog) clearTimeout(watchdog);
  watchdog = setTimeout(() => {
    if (runActive) status("⚠ no activity for a while — an agent may be stalled", false);
  }, 25000);
}
function onTurn(e) {
  const cop = $("tok-cop"), thief = $("tok-thief");
  if (e.role === "cop") { trail("cop", +cop.dataset.r || G.rows - 1, +cop.dataset.c || G.cols - 1); }
  else { trail("thief", +thief.dataset.r || 0, +thief.dataset.c || 0); }
  place(cop, e.cop_pos[0], e.cop_pos[1]); place(thief, e.thief_pos[0], e.thief_pos[1]);
  cop.dataset.r = e.cop_pos[0]; cop.dataset.c = e.cop_pos[1];
  thief.dataset.r = e.thief_pos[0]; thief.dataset.c = e.thief_pos[1];
  document.querySelector(".agent.cop").classList.toggle("active", e.role === "cop");
  document.querySelector(".agent.thief").classList.toggle("active", e.role === "thief");
  (e.barriers || []).forEach((b) => {
    const cell = $("grid").children[b[0] * G.cols + b[1]];
    if (cell) cell.classList.add("barrier");
  });
  markVision("cop", e.cop_pos[0], e.cop_pos[1]);
  markVision("thief", e.thief_pos[0], e.thief_pos[1]);
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
    if (n > 1) v.textContent = win === "cop" ? "BUSTED" : win === "thief" ? "GETAWAY" : "DEAD HEAT";
    else v.textContent = win === "cop" ? "BUSTED" : "ESCAPED";
    const tape = (r.games || []).map((g) => (g.winner === "cop" ? "🚓" : "🚗")).join(" ");
    const s = document.createElement("small");
    s.textContent = tape + "   cop " + r.cop_score + " · thief " + r.thief_score;
    v.appendChild(s);
  }
  v.classList.remove("hidden");
}
function handle(e) {
  resetWatchdog();
  if (e.type === "meta") onMeta(e);
  else if (e.type === "turn") onTurn(e);
  else if (e.type === "sub_game_end") onSubGameEnd(e);
  else if (e.type === "game_end") onEnd(e);
  else if (e.type === "error") status("⚠ " + e.message, false);
  else if (e.type === "done") {
    runActive = false;
    if (watchdog) clearTimeout(watchdog);
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
  runActive = true; status("● establishing secure link…", true); resetWatchdog();
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(proto + "//" + location.host + "/api/ws/" + res.run_id);
  ws.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (err) { /* skip */ } };
  ws.onerror = () => status("⚠ connection error", false);
  ws.onclose = () => {
    if (!runActive) return;
    runActive = false;
    if (watchdog) clearTimeout(watchdog);
    status("⚠ link lost — press engage to retry", false);
    $("engage").disabled = false; $("newmatch").classList.remove("hidden");
  };
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
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".copy");
  if (!btn) return;
  const code = $(btn.dataset.copy);
  if (!code) return;
  navigator.clipboard.writeText((code.textContent || "").trim()).then(() => {
    const prev = btn.textContent; btn.textContent = "✓";
    setTimeout(() => { btn.textContent = prev; }, 1200);
  }).catch(() => {});
});
loadInfo();
requestAnimationFrame(idleBoard);
