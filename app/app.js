/* JARVIS · LINK 모바일 앱 — 데이터: ../data/dashboard.json / 명령: GitHub Actions 실행 */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const store = {
  get(k, d = "") { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k); } catch { /* 저장 불가 환경 */ } },
};

const guessRepo = () => {
  const host = location.hostname.match(/^([\w-]+)\.github\.io$/);
  const seg = location.pathname.split("/").filter(Boolean)[0];
  return host && seg ? `${host[1]}/${seg}` : "gogonaver12-bot/link";
};
let REPO = guessRepo();
let D = null;          // dashboard.json
let bizFilter = "all";

const NAMES = { anthropic: "Claude", gemini: "Gemini", groq: "Groq", cerebras: "Cerebras", openrouter: "OpenRouter", mistral: "Mistral",
  ollama: "Ollama", openai: "ChatGPT", deepseek: "DeepSeek", xai: "Grok", qwen: "Qwen", moonshot: "Kimi", together: "Together",
  upstage: "Upstage Solar", clova: "HyperCLOVA X", perplexity: "Perplexity" };
const STATUS = { active: "진행중", candidate: "후보", killed: "탈락" };
const ACTION = { scale: "확장", upgrade: "개선", kill: "탈락", watch: "관찰" };
const CRIT = { demand: "수요", low_competition: "낮은 경쟁", low_cost: "낮은 비용", speed_to_revenue: "수익 속도", scalability: "확장성", low_risk: "낮은 위험" };
const usd = (n) => "$" + Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: n < 10 ? 2 : 0 });
const ago = (iso) => {
  if (!iso) return "";
  const m = Math.round((Date.now() - new Date(iso)) / 60000);
  return m < 1 ? "방금" : m < 60 ? `${m}분 전` : m < 1440 ? `${Math.round(m / 60)}시간 전` : `${Math.round(m / 1440)}일 전`;
};
const q = (s) => '"' + String(s).replace(/["\\]/g, "\\$&") + '"';  // 명령 인자 따옴표 처리(shlex 호환)
const hue = (s) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);

/* ───────── 안전한 마크다운 렌더러 (HTML 전부 이스케이프 후 변환) ───────── */
function md(src) {
  const inline = (t) => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/(^|\s)(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');
  const out = []; let list = null, code = null, table = null;
  const flush = () => { if (list) { out.push(`<${list.t}>${list.items.join("")}</${list.t}>`); list = null; }
    if (table) { out.push(`<table>${table.join("")}</table>`); table = null; } };
  for (const line of String(src).split("\n")) {
    if (line.startsWith("```")) { if (code) { out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`); code = null; } else { flush(); code = []; } continue; }
    if (code) { code.push(line); continue; }
    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)/))) { flush(); out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); }
    else if ((m = line.match(/^\s*[-*]\s+(.*)/)) || (m = line.match(/^\s*\d+[.)]\s+(.*)/))) {
      const t = /^\s*\d/.test(line) ? "ol" : "ul";
      if (table) flush();
      if (!list || list.t !== t) { flush(); list = { t, items: [] }; }
      list.items.push(`<li>${inline(m[1])}</li>`);
    } else if (/^\s*\|.*\|\s*$/.test(line)) {
      if (list) flush();
      if (/^\s*\|[\s:|-]+\|\s*$/.test(line)) continue;
      table = table || [];
      const cells = line.trim().slice(1, -1).split("|").map((c) => inline(c.trim()));
      const tag = table.length ? "td" : "th";
      table.push(`<tr>${cells.map((c) => `<${tag}>${c}</${tag}>`).join("")}</tr>`);
    } else if ((m = line.match(/^>\s?(.*)/))) { flush(); out.push(`<blockquote>${inline(m[1])}</blockquote>`); }
    else if (!line.trim()) flush();
    else { flush(); out.push(`<p>${inline(line)}</p>`); }
  }
  if (code) out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`);
  flush();
  return out.join("");
}

/* ───────── 데이터 ───────── */
async function fetchText(path) {
  const urls = [`../${path}?t=${Date.now()}`, `https://raw.githubusercontent.com/${REPO}/main/${path}?t=${Date.now()}`];
  for (const u of urls) {
    try { const r = await fetch(u, { cache: "no-store" }); if (r.ok) return await r.text(); } catch { /* 다음 주소 시도 */ }
  }
  throw new Error("불러오기 실패");
}
async function load(silent) {
  try {
    D = JSON.parse(await fetchText("data/dashboard.json"));
    if (D.repo) REPO = D.repo;
    $("#company").textContent = D.company || "LINK AI Company";
    if (!silent) toast("최신 데이터로 갱신했어요");
  } catch {
    if (!D) D = { empty: true };
    if (!silent) toast("데이터를 불러오지 못했어요. 잠시 후 다시 시도해 주세요");
  }
  render();
}

/* ───────── GitHub 실행 ───────── */
const token = () => store.get("gh_token");
async function gh(path, opts = {}) {
  const r = await fetch("https://api.github.com" + path, { ...opts, headers: {
    Accept: "application/vnd.github+json", Authorization: "Bearer " + token(), "X-GitHub-Api-Version": "2022-11-28",
    ...(opts.body ? { "Content-Type": "application/json" } : {}) } });
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 100)}`);
  return r.status === 204 ? null : r.json();
}
async function dispatch(command = "daily", goal = "", label = "") {
  const text = goal || command;
  if (!token()) {
    try { await navigator.clipboard.writeText(text); } catch { /* 복사 불가 */ }
    openSheet(noTokenSheet(text));
    return;
  }
  try {
    await gh(`/repos/${REPO}/actions/workflows/mother.yml/dispatches`, { method: "POST",
      body: JSON.stringify({ ref: "main", inputs: { command, goal } }) });
    closeSheet();
    store.set("last_run", JSON.stringify({ label: label || cmdName(command), cmd: command, ts: Date.now() }));
    RUN = { status: "queued", label: label || cmdName(command), started: Date.now(), steps: [] }; render();
    toast(`🚀 ${label || "명령"} 실행 시작 — 진행률은 위에서 실시간으로 보여요`);
    setTimeout(pollRun, 4000);
  } catch (e) {
    openSheet(tokenFixSheet(String(e.message).slice(0, 3)));
  }
}
let polling = 0, RUN = null;
const EXPECT = [[/스토리|다음 화/, 600], [/영상|shorts/, 330], [/일일|daily/, 1200], [/테스트|토너먼트|test/, 240], [/사업 발굴|scout/, 420], [/파이프라인/, 300]];
const STEPNAME = { "Set up job": "준비", "Run actions/checkout@v4": "코드 받기", "Run actions/setup-python@v5": "파이썬 준비",
  "Run pip install -r requirements.txt": "도구 설치", "install ffmpeg (숏츠 영상 제작용)": "영상 도구 설치", run: "AI 작업 중", "save results": "결과 저장" };
function runCard() {
  if (!RUN) return "";
  const done = RUN.status === "completed", ok = RUN.conclusion === "success";
  const exp = (EXPECT.find(([re]) => re.test(RUN.label || "")) || [0, 300])[1];
  const sec = Math.max(0, ((RUN.ended || Date.now()) - RUN.started) / 1000);
  const pct = done ? 100 : Math.min(95, Math.round(sec / exp * 100));
  const mmss = (s) => `${Math.floor(s / 60)}분 ${String(Math.floor(s % 60)).padStart(2, "0")}초`;
  const steps = (RUN.steps || []).filter((s) => STEPNAME[s.name]);
  return `<div class="card run-card ${done ? (ok ? "ok" : "bad") : ""}"><div class="row" style="padding:0">
    <span class="dot ${done ? (ok ? "" : "bad") : "warn"}"></span><div class="grow"><div class="t">${esc(RUN.label || "실행")} · ${done ? (ok ? "완료" : "실패") : RUN.status === "queued" ? "대기 중" : "진행 중"}</div>
    <div class="m">${mmss(sec)} 경과${done ? "" : ` · 보통 ${Math.round(exp / 60)}분`}</div></div><b class="pct">${pct}%</b></div>
    <div class="bar run"><i style="width:${pct}%"></i></div>
    ${steps.length ? `<div class="run-steps">${steps.map((s) => `<span class="${s.status === "completed" ? (s.conclusion === "success" || s.conclusion === "skipped" ? "on" : "bad") : s.status === "in_progress" ? "now" : ""}">${STEPNAME[s.name]}</span>`).join("")}</div>` : ""}
    ${done ? `<button class="btn small ghost" style="margin-top:10px" data-go="${/영상/.test(RUN.label) ? "#videos" : "#home"}">${/영상/.test(RUN.label) ? "▶️ 만든 영상 보기" : "결과 보기"}</button>` : ""}</div>`;
}
function paintRun() { const el = $("#runbox"); if (el) el.innerHTML = runCard(); }
setInterval(() => { if (RUN && RUN.status !== "completed") paintRun(); }, 1000);
async function pollRun() {
  if (polling) return;
  const chip = $("#runchip");
  for (polling = 1; polling < 80; polling++) {
    try {
      const j = await gh(`/repos/${REPO}/actions/workflows/mother.yml/runs?per_page=1`);
      const run = j.workflow_runs[0];
      if (!run) break;
      const last = JSON.parse(store.get("last_run") || "{}");
      const mine = last.ts && Math.abs(new Date(run.created_at) - last.ts) < 180000;
      if (run.status === "completed" && polling === 1 && Date.now() - new Date(run.updated_at) > 600000) break;  // 오래전에 끝난 실행은 표시 안 함
      let steps = [];
      try { steps = ((await gh(`/repos/${REPO}/actions/runs/${run.id}/jobs`)).jobs[0] || {}).steps || []; } catch { /* 단계 정보 없음 */ }
      RUN = { status: run.status, conclusion: run.conclusion, label: mine ? last.label : run.event === "schedule" ? "일일 자동운영" : "자동 실행",
              started: new Date(run.run_started_at || run.created_at).getTime(), ended: run.status === "completed" ? new Date(run.updated_at).getTime() : 0, steps };
      paintRun();
      chip.hidden = false;
      if (run.status !== "completed") { chip.className = "runchip"; chip.textContent = run.status === "queued" ? "대기 중" : "실행 중…"; }
      else {
        const ok = run.conclusion === "success";
        chip.className = "runchip " + (ok ? "ok" : "bad");
        chip.textContent = ok ? "완료" : "실패";
        toast(ok ? "✅ 완료! 결과를 불러오는 중…" : "⚠️ 실행 실패 — 다음 세션에서 자동 수정돼요");
        setTimeout(() => load(true), 60000);
        setTimeout(() => { chip.hidden = true; RUN = null; paintRun(); }, 180000);
        break;
      }
    } catch { break; }
    await new Promise((r) => setTimeout(r, 15000));
  }
  polling = 0;
}

/* ───────── 공통 UI ───────── */
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("show"), 3200);
}
function openSheet(html) { $("#sheetBody").innerHTML = html; $("#sheet").hidden = false; document.body.style.overflow = "hidden"; }
function closeSheet() { $("#sheet").hidden = true; document.body.style.overflow = ""; }
const empty = (icon, title, text, btn) => `<div class="card empty"><div class="big">${icon}</div><b>${title}</b>${text}
  ${btn ? `<div style="margin-top:14px"><button class="btn small" ${btn.attr}>${btn.label}</button></div>` : ""}</div>`;

/* ───────── 화면: 홈 ───────── */
function ringSvg(pct, label) {
  const r = 52, c = 2 * Math.PI * r, v = Math.min(1, Math.max(0, pct));
  const color = v > .9 ? "var(--bad)" : v > .7 ? "var(--warn)" : "url(#g)";
  return `<svg viewBox="0 0 140 140" role="img" aria-label="오늘 AI 비용 ${Math.round(v * 100)}%">
    <defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent2)"/></linearGradient></defs>
    <circle class="spin" cx="70" cy="70" r="66" stroke="var(--line2)" stroke-width="1" stroke-dasharray="3 7"/>
    <circle class="spin2" cx="70" cy="70" r="60" stroke="var(--accent)" stroke-opacity=".35" stroke-width="2" stroke-dasharray="40 18 6 18"/>
    <circle cx="70" cy="70" r="${r}" stroke="var(--card2)" stroke-width="8"/>
    <circle cx="70" cy="70" r="${r}" stroke="${color}" stroke-width="8" stroke-linecap="round"
      stroke-dasharray="${c * v} ${c}" transform="rotate(-90 70 70)"/>
    <text class="val" x="70" y="72" text-anchor="middle">${esc(label)}</text>
    <text class="cap" x="70" y="90" text-anchor="middle">TODAY AI COST</text></svg>`;
}
function viewHome() {
  if (D.empty) return `<div class="skeleton"></div><div class="skeleton"></div>`;
  const b = D.budget, money = D.money, act = D.ideas.filter((i) => i.status === "active");
  const scored = D.team.filter((t) => t.avg != null);
  const teamAvg = scored.length ? (scored.reduce((a, t) => a + t.avg, 0) / scored.length).toFixed(1) : "–";
  const errs = D.errors.length;
  const conn = D.providers.filter((p) => p.connected).length;
  const now = new Date();
  return `<div id="runbox">${runCard()}</div>
  <section class="card hero">
    <div class="ring">${ringSvg(b.today / b.daily, usd(b.today))}</div>
    <div class="hero-info">
      <div class="clock" id="clock">${now.toTimeString().slice(0, 5)}</div>
      <div class="date">${now.toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "long" })}</div>
      <span class="state"><span class="dot ${errs ? "bad" : conn ? "" : "warn"}"></span>${errs ? `문제 ${errs}건 · 자동 해결 중` : conn ? `시스템 정상 · AI ${conn}개 연결` : "AI 키 연결 필요"}</span>
      <div class="upd">예산 ${usd(b.daily)}/일 · 갱신 ${ago(D.updated)}</div>
    </div>
  </section>
  ${D.progress ? `<div class="card" style="margin-top:10px"><div class="t">진행 단계</div>
    <div class="steps">${D.progress.steps.map((st, k) => `<div class="step ${st.done ? "on" : ""}"><b>${st.done ? "✓" : k + 1}</b><span>${esc(st.name)}</span><small>${k === 4 ? usd(st.n) : st.n}</small></div>`).join("")}</div>
    ${D.progress.blocker ? `<div class="note" style="color:var(--fg)">⛔ ${esc(D.progress.blocker)}</div>
      ${{ google: '<button class="btn small" style="margin-top:8px" data-open="google">🔑 구글 연결 방법</button>',
          scout: '<button class="btn small" style="margin-top:8px" data-open="scout">🔎 사업 발굴</button>',
          log: '<button class="btn small" style="margin-top:8px" data-open="log">💵 매출 기록</button>' }[D.progress.action] || ""}` : ""}</div>` : ""}
  ${D.studio ? (() => { const S = D.studio, V = D.videos || [], L = S.last;
    return `<div class="card tap" data-go="#make" style="margin-top:10px"><div class="row"><div class="score" style="font-size:20px">🎬</div>
      <div class="grow"><div class="t">영상 파트 · ${esc(S.channel)}</div><div class="m">올린 영상 ${V.length}개 · 조회 ${V.reduce((a, v) => a + v.views, 0).toLocaleString()}회 · 대기 대본 ${S.queue_total}개</div>
      ${L ? `<div class="m">${L.ok ? "✅" : "⚠️"} 최근 제작 ${ago(L.ts)}</div>` : ""}</div><span class="m">›</span></div></div>`; })() : ""}
  <div class="kpis">
    <div class="card kpi"><div class="lbl">💰 총매출</div><div class="num">${usd(money.revenue)}</div></div>
    <div class="card kpi"><div class="lbl">📈 순이익</div><div class="num ${money.profit >= 0 ? "pos" : "neg"}">${usd(money.profit)}</div></div>
    <div class="card kpi tap" data-go="#biz"><div class="lbl">🚀 진행 사업</div><div class="num">${act.length}<small>/ ${D.ideas.length}</small></div></div>
    <div class="card kpi tap" data-go="#team"><div class="lbl">🧠 팀 평균</div><div class="num">${teamAvg}<small>점</small></div></div>
  </div>
  ${errs ? `<div class="card alert tap" data-errlog="0" style="margin-top:10px"><div class="t">⚠️ 해결 중인 문제</div><div class="m wrap clamp2">${esc(D.errors[0].msg || D.errors[0].error)}</div></div>` : ""}
  ${(D.commands || []).length ? `<div class="section-title"><h2>최근 명령 결과</h2></div><div class="card">${D.commands.slice(0, 4).map(cmdRow).join("")}</div>` : ""}
  <div class="section-title"><h2>빠른 실행</h2></div>
  <div class="quick">
    <button class="qbtn" data-cmd="daily" data-label="일일 자동운영"><span class="ico">⚙️</span>일일 자동운영</button>
    <button class="qbtn" data-open="scout"><span class="ico">🔎</span>사업 발굴</button>
    <button class="qbtn" data-cmd="biz review" data-label="ROI 리뷰"><span class="ico">📊</span>ROI 리뷰</button>
    <button class="qbtn" data-cmd="agent upgrade" data-label="팀 업그레이드"><span class="ico">🧬</span>팀 업그레이드</button>
    <button class="qbtn" data-open="log"><span class="ico">💵</span>매출 기록</button>
    <button class="qbtn" data-cmd="jobs" data-label="작업큐 처리"><span class="ico">📥</span>작업큐 처리</button>
  </div>
  ${(D.news || []).length ? `<div class="section-title"><h2>오늘의 트렌드</h2></div><div class="card">${D.news.slice(0, 8).map((n) => `
    <div class="row"><span class="pill ${n.category === "trend" ? "accent" : ""}">${esc(n.source.startsWith("구글 트렌드 ") ? "🔥" + n.source.slice(7) : n.source.split(" ")[0])}</span>
    <div class="grow"><a class="t" style="display:block;color:var(--fg)" href="${/^https?:\/\//.test(n.url) ? esc(n.url) : "#"}" target="_blank" rel="noopener noreferrer">${esc(n.title)}</a></div></div>`).join("")}</div>` : ""}
  <div class="section-title"><h2>최근 활동</h2></div>
  ${D.runs.length ? `<div class="card">${D.runs.slice(0, 5).map((r) => `
    <div class="row"><div class="avatar" style="background:hsl(${hue(r.agent)} 70% 45%)">${esc(r.agent[0].toUpperCase())}</div>
    <div class="grow"><div class="t">${esc(r.task)}</div><div class="m">${esc(r.agent)} · ${esc(r.model || "실패")} · ${ago(r.ts)}</div></div></div>`).join("")}</div>`
    : empty("🛰️", "아직 활동이 없어요", "아래 ⚡명령 버튼으로 첫 목표를 내려보세요")}
  <div class="section-title"><h2>최근 보고서</h2><a href="#reports">전체</a></div>
  ${D.reports.length ? `<div class="card">${D.reports.slice(0, 3).map(reportRow).join("")}</div>` : empty("📄", "보고서가 아직 없어요", "일일 자동운영을 실행하면 매일 쌓여요")}`;
}
const CMDNAME = [[/^story new/, "새 AI 스토리 + 1화"], [/^story next/, "AI 스토리 다음 화"], [/^shorts --skip/, "대본 빼기"], [/^shorts.*--private/, "영상 테스트 제작"], [/^shorts/, "영상 제작"],
  [/^benchmark/, "인기 영상 분석"], [/^test all/, "생존 토너먼트"], [/^test /, "생존 테스트·개선"], [/^blog/, "블로그 글"], [/^pipeline run/, "파이프라인 실행"], [/^pipeline new/, "파이프라인 만들기"], [/^daily$|^schedule$/, "일일 자동운영"], [/^biz scout/, "사업 발굴"], [/^biz review/, "ROI 리뷰"], [/^biz approve/, "사업 승인"],
  [/^biz log/, "매출 기록"], [/^agent upgrade/, "팀 업그레이드"], [/^agent new/, "새 팀 만들기"], [/^jobs$|^push$/, "작업큐 처리"],
  [/^ai arena/, "AI 대결"], [/^ai ask/, "AI 질문"], [/^news add/, "사이트 추가"], [/^news/, "정보 수집"], [/^export$/, "데이터 갱신"]];
const cmdName = (c) => { const hit = CMDNAME.find(([re]) => re.test(c || "")); return hit ? hit[1] + (/--market (\w+)/.exec(c) ? " " + /--market (\w+)/.exec(c)[1] : "") : "목표: " + (c || "").slice(0, 30); };
const cmdRow = (c, i) => `<div class="row tap" data-cmdlog="${i}"><span class="dot ${c.ok ? "" : "bad"}"></span>
  <div class="grow"><div class="t">${esc(cmdName(c.cmd))} ${c.ok ? "" : "· 실패"}</div><div class="m">${esc((c.output || "").split("\n").filter(Boolean).slice(-1)[0] || "")}</div></div>
  <span class="m">${ago(c.ts)}</span></div>`;
const reportRow = (r) => `<div class="row tap" data-go="#report=${encodeURIComponent(r.file)}"><div class="score" style="font-size:17px">📄</div>
  <div class="grow"><div class="t">${esc(r.title)}</div><div class="m">${ago(r.date)} · ${esc(r.file.replace("reports/", ""))}</div></div></div>`;

/* ───────── 화면: 사업 ───────── */
function viewBiz() {
  if (D.empty) return `<div class="skeleton"></div>`;
  const list = D.ideas.filter((i) => bizFilter === "all" || i.status === bizFilter).sort((a, b) => b.score - a.score);
  const cnt = (s) => D.ideas.filter((i) => s === "all" || i.status === s).length;
  return `<h1 class="page">사업</h1><p class="sub">발굴 → 생존 테스트 → 실행 → ROI 판정 · 살아남은 것만 진행</p>
  <button class="btn ghost" style="margin-bottom:12px" data-cmd="test all" data-label="전체 생존 테스트">🧪 전체 생존 테스트 (사업·파이프라인)</button>
  <div class="seg">${["all", "active", "candidate", "killed"].map((s) =>
    `<button data-filter="${s}" class="${bizFilter === s ? "on" : ""}">${s === "all" ? "전체" : STATUS[s]} ${cnt(s)}</button>`).join("")}</div>
  ${list.length ? list.map((i) => {
    const m = i.metrics, lr = i.last_review;
    return `<div class="card tap" data-idea="${esc(i.id)}"><div class="row">
      <div class="score">${Math.round(i.score)}</div>
      <div class="grow"><div class="t">${esc(i.title)}</div><div class="m">${esc(i.market)} · ${esc(i.platform)} · ${esc(i.model)}</div></div>
      <span class="pill ${esc(i.status)}">${STATUS[i.status] || esc(i.status)}</span></div>
      ${i.viability ? `<div class="m" style="margin-top:6px">🧪 흑자 확률 ${Math.round(i.viability.sim.p_profit * 100)}% · 90일 ${usd(i.viability.sim.rev_p50)}${i.killed_by ? " · " + esc(i.killed_by) + " 탈락" : ""}</div>` : ""}
      ${m ? `<div class="chips"><span class="pill">매출 ${usd(m.revenue)}</span><span class="pill ${m.roi >= 0 ? "ok" : "bad"}">ROI ${(m.roi * 100).toFixed(0)}%</span>
        <span class="pill">${m.age}일차</span>${lr ? `<span class="pill ${esc(lr.action)}">${ACTION[lr.action] || ""}</span>` : ""}</div>` : ""}</div>`;
  }).join("") : empty("💡", "아직 사업 아이디어가 없어요", "AI가 국가별로 돈 되는 사업을 찾아 점수를 매겨요", { attr: 'data-open="scout"', label: "🔎 사업 발굴 시작" })}`;
}
const fileUrl = (f) => `../${f.split("/").map(encodeURIComponent).join("/")}`;
function viaBox(i) {
  const v = i.viability;
  if (!v) return i.status === "killed" ? "" : `<div class="field"><label>🧪 생존 테스트</label><div class="card"><div class="m wrap">인터넷 조사 → AI 3개 경쟁 추정 → 2,000번 수익 시뮬레이션으로 살아남을지 판정해요</div>
    <button class="btn" style="margin-top:12px" data-cmd="test ${esc(i.id)}" data-label="생존 테스트">🧪 테스트하기</button></div></div>`;
  const s = v.sim;
  return `<div class="field"><label>🧪 생존 테스트 · ${esc(v.date)}</label><div class="card">
    <div class="row"><span class="pill ${v.pass ? "ok" : v.hold ? "candidate" : "bad"}">${v.pass ? "생존" : v.hold ? "보류" : "탈락"}</span><div class="grow m wrap">${esc(v.why)}</div></div>
    <div class="kv"><div><b>${Math.round(s.p_profit * 100)}%</b><span>흑자 확률</span></div><div><b>${(s.roi_p50 * 100).toFixed(0)}%</b><span>ROI 중앙</span></div>
      <div><b>${usd(s.rev_p50)}</b><span>90일 매출</span></div><div><b>${s.breakeven_p50 > s.days ? "–" : s.breakeven_p50 + "일"}</b><span>손익분기</span></div></div>
    <div class="note">90일 매출 범위(비관~낙관): ${usd(s.rev_p10)} ~ ${usd(s.rev_p90)} · ${s.runs.toLocaleString()}번 시뮬레이션</div>
    ${(v.estimates || []).length ? `<div class="note"><b>AI 경쟁 추정</b>${v.estimates.map((e) => `<div>· ${esc(e.role)} <span class="m">${esc(e.model)}</span> — 가격 ${usd(e.price_usd)}, 전환 ${esc(e.conv_rate_pct)}%, 하루 ${esc(e.visitors_low)}~${esc(e.visitors_high)}명</div>`).join("")}</div>` : ""}
    ${(v.risks || []).length ? `<div class="note"><b>위험</b> ${v.risks.map(esc).join(" · ")}</div>` : ""}
    ${(v.evidence || []).length ? `<div class="note md"><b>근거</b>${md(v.evidence.map((x) => "- " + x).join("\n"))}</div>` : ""}
    <button class="btn ghost small" style="margin-top:10px" data-cmd="test ${esc(i.id)}" data-label="생존 테스트">${i.status === "killed" ? "🩺 개선해서 살리기" : "🔁 다시 테스트"}</button></div></div>`;
}
function upBox(ups, ver) {  // 탈락 → 진단 → 개선안 → 재테스트 기록
  if (!(ups || []).length) return "";
  return `<div class="field"><label>🔧 자동 개선 기록${ver > 1 ? " · 지금 v" + ver : ""}</label><div class="card">${ups.map((u) => u.error
    ? `<div class="m">⚠️ 개선안 만들기 실패: ${esc(u.error)}</div>`
    : `<div class="row" style="align-items:flex-start"><span class="pill ${u.pass ? "ok" : u.adopted ? "candidate" : "bad"}">${u.round}차 ${u.pass ? "생존" : u.adopted ? "채택" : "버림"}</span>
      <div class="grow"><div class="t wrap">${esc(u.title)}</div><div class="m wrap">🩺 ${esc((u.diagnosis || []).join(" · "))}</div>
      <div class="m wrap">🔧 ${esc((u.changes || []).join(" · "))}</div><div class="m wrap">📊 ${esc(u.result)}</div></div></div>`).join("")}</div></div>`;
}
function productBox(i) {
  const pr = i.product;
  if (i.status === "killed") return "";
  if (!pr) return `<div class="field"><label>판매할 상품</label><div class="card"><div class="m wrap">AI가 목차·장별 원고·PDF·판매 페이지 문구까지 한 번에 만들어요 (무료 AI 사용, 약 3~5분)</div>
    <button class="btn" style="margin-top:12px" data-cmd="make ${esc(i.id)}" data-label="상품 만들기">🛠 상품 만들기</button></div></div>`;
  const listing = `${pr.dir}/판매페이지.md`;
  return `<div class="field"><label>📦 만든 상품 · ${esc(pr.made)}</label><div class="card"><div class="t wrap">${esc(pr.title)}</div>
    <div class="m">${pr.files.length}개 파일</div><div class="btns">
    ${pr.pdf ? `<a class="btn" style="text-align:center" href="${fileUrl(pr.pdf)}" target="_blank" rel="noopener">📕 PDF 보기</a>` : ""}
    <button class="btn ghost" data-go="#report=${encodeURIComponent(listing)}">🛒 판매 페이지</button></div>
    <button class="btn ghost" style="margin-top:8px" data-cmd="make ${esc(i.id)}" data-label="상품 다시 만들기">🔁 다시 만들기</button></div></div>`;
}
function ideaSheet(id) {
  const i = D.ideas.find((x) => x.id === id); if (!i) return "";
  const m = i.metrics, lr = i.last_review;
  return `<h3>${esc(i.title)}</h3><div class="chips"><span class="pill ${esc(i.status)}">${STATUS[i.status] || ""}</span>
    <span class="pill accent">${esc(i.market)}</span><span class="pill">${esc(i.platform)}</span><span class="pill">${Math.round(i.score)}점</span></div>
  ${m ? `<div class="kv"><div><b>${usd(m.revenue)}</b><span>매출</span></div><div><b>${usd(m.cost)}</b><span>비용</span></div>
    <div><b class="${m.roi >= 0 ? "pos" : "neg"}">${(m.roi * 100).toFixed(0)}%</b><span>ROI</span></div><div><b>${m.age}</b><span>일차</span></div></div>` : ""}
  ${lr && lr.plan ? `<div class="field"><label>최근 판정: ${ACTION[lr.action] || ""}</label><div class="card md">${md(lr.plan)}</div></div>` : ""}
  <div class="field"><label>오늘 바로 할 첫 행동</label><div class="card">${esc(i.first_step)}</div></div>
  <div class="field"><label>점수 상세</label>${Object.entries(i.scores || {}).map(([k, v]) =>
    `<div class="crit"><span>${CRIT[k] || esc(k)}</span><div class="bar"><i style="width:${Math.max(0, Math.min(100, v))}%"></i></div><b>${v}</b></div>`).join("")}</div>
  <div class="field"><label>근거</label><div class="card md">${md(i.evidence || "")}</div></div>
  ${viaBox(i)}
  ${upBox(i.upgrades, i.version)}
  ${productBox(i)}
  <div class="btns">${i.status === "candidate" ? `<button class="btn" data-cmd="biz approve ${esc(i.id)}" data-label="사업 승인">✅ 승인하고 시작</button>`
    : `<button class="btn ghost" data-cmd="biz review" data-label="ROI 리뷰">📊 다시 판정</button>`}
    <button class="btn ghost" data-open="log" data-id="${esc(i.id)}">💵 매출 기록</button></div>`;
}

/* ───────── 화면: 팀 ───────── */
function viewTeam() {
  if (D.empty) return `<div class="skeleton"></div>`;
  return `<h1 class="page">팀</h1><p class="sub">점수가 낮은 팀은 프롬프트가 자동으로 업그레이드돼요</p>
  ${D.team.map((t) => `<div class="card"><div class="row">
    <div class="avatar" style="background:linear-gradient(135deg,hsl(${hue(t.name)} 75% 52%),hsl(${(hue(t.name) + 50) % 360} 70% 45%))">${esc(t.title[0])}</div>
    <div class="grow"><div class="t">${esc(t.title)}</div><div class="m">${esc(t.name)} · v${t.version} · ${t.model === "auto" ? "무료 AI 우선" : esc(t.model)}</div></div>
    <div class="score">${t.avg ?? "–"}</div></div>
    <div class="bar ${t.avg != null && t.avg < 6.5 ? "bad" : ""}"><i style="width:${(t.avg || 0) * 10}%"></i></div>
    <div class="chips">${t.tools.map((x) => `<span class="pill">${esc(x)}</span>`).join("")}${t.skills.map((x) => `<span class="pill accent">⚡${esc(x)}</span>`).join("")}</div>
    ${t.last_feedback ? `<div class="note">💬 ${esc(t.last_feedback)}</div>` : ""}</div>`).join("")}
  <div class="btns"><button class="btn ghost" data-cmd="agent upgrade" data-label="팀 업그레이드">🧬 팀 업그레이드</button>
    <button class="btn" data-open="newagent">＋ 새 팀 만들기</button></div>`;
}

/* ───────── 화면: 영상 제작 ───────── */
function viewMake() {
  if (D.empty) return `<div class="skeleton"></div>`;
  const S = D.studio || {}, av = S.ai_video || {}, L = S.last;
  const chip = (ok, on, off, open) => `<span class="pill ${ok ? "ok" : "candidate"} ${!ok && open ? "tap" : ""}" ${!ok && open ? `data-open="${open}"` : ""}>${ok ? "✓ " + on : "✗ " + off}</span>`;
  const li = L ? (D.commands || []).findIndex((c) => c.ts === L.ts) : -1;
  return `<div id="runbox">${runCard()}</div>${makeSeg("shorts")}<h1 class="page">🎬 영상 제작</h1><p class="sub">${esc(S.channel || "")} · 매일 아침 ${S.per_day || 1}개 자동 제작</p>
  <div class="card"><div class="t">준비 상태</div><div class="chips">
    ${chip(S.new_channel, "새 채널 연결됨", "새 채널 미연결 → 비공개로 올림", "newchan")}
    ${chip(S.music, "배경음악", "배경음악 없음(효과음만)", "music")}
    ${chip(av.on, `AI 영상 ${usd(av.spent)}/${usd(av.budget)}`, "AI 영상 꺼짐")}
    ${chip(S.ai_images, "AI 이미지", "AI 이미지 꺼짐")}</div>
    ${S.concept ? `<div class="note">🧪 ${esc(S.concept)}</div>` : ""}</div>
  <div class="section-title"><h2>지금 만들기</h2></div>
  <div class="card"><div class="field" style="margin-top:0"><label>주제 (비우면 AI가 인기 영상 분석해서 골라요)</label>
    <input id="vTopic" maxlength="120" placeholder="예: AI한테 내 하루 일정 짜달라 했더니"></div>
    <div class="btns"><button class="btn ghost" id="vTest">🔒 테스트</button><button class="btn" id="vMake">🚀 만들기</button></div>
    <div class="m" style="margin-top:8px">대본 → 훅 채점 → 표지 문구 → 영상·음악·자막 → 업로드 · 약 5분 · 끝나면 ‘영상확인’에 떠요</div></div>
  <div class="quick" style="margin-top:10px">
    <button class="qbtn" data-cmd="benchmark" data-label="인기 영상 분석"><span class="ico">📈</span>인기 영상 분석</button>
    <button class="qbtn" data-go="#videos"><span class="ico">▶️</span>영상 확인</button>
    <button class="qbtn" data-open="music"><span class="ico">🎵</span>음악 등록</button></div>
  ${L ? `<div class="section-title"><h2>최근 제작 결과</h2></div><div class="card">${li >= 0 ? cmdRow(L, li)
    : `<div class="row"><span class="dot ${L.ok ? "" : "bad"}"></span><div class="grow"><div class="t">${esc(cmdName(L.cmd))}</div><div class="m">${ago(L.ts)}</div></div></div>`}</div>` : ""}
  <div class="section-title"><h2>대기 중인 대본 ${S.queue_total || 0}개</h2></div>
  ${(S.queue || []).length ? `<div class="card">${S.queue.map((x) => `<div class="row"><div class="score" style="color:${x.score < 50 ? "var(--warn)" : "var(--ok)"}">${x.score}</div>
      <div class="grow"><div class="t">${esc(x.title)}</div><div class="m clamp2">🎣 ${esc(x.hook)} · ${x.lines}문장</div></div>
      <button class="btn small ghost" data-cmd="shorts --skip ${esc(x.id)}" data-label="대본 빼기">빼기</button></div>`).join("")}
    <div class="note">숫자 = 훅 점수 · 50점 미만은 AI가 고쳐 쓰고 만들어요 · 최신 대본부터 제작</div></div>`
    : empty("📝", "대기 중인 대본이 없어요", "만들기를 누르면 AI가 대본부터 써요")}`;
}

const makeSeg = (on) => `<div class="seg"><a href="#make" class="${on === "shorts" ? "on" : ""}">🎬 정보 숏츠</a><a href="#story" class="${on === "story" ? "on" : ""}">🎭 AI 실사 스토리</a></div>`;
const GENRES = ["판타지", "SCP 인터뷰", "로맨스", "호러", "SF", "학원물"];

/* ───────── 화면: AI 실사 스토리 ───────── */
function viewStory() {
  if (D.empty) return `<div class="skeleton"></div>`;
  const SS = D.stories || [], S = D.studio || {};
  const imgUrl = (p) => `../${p.split("/").map(encodeURIComponent).join("/")}`;
  return `<div id="runbox">${runCard()}</div>${makeSeg("story")}<h1 class="page">🎭 AI 실사 스토리</h1>
  <p class="sub">인물 사진을 먼저 만들고 장면마다 같은 얼굴로 그려요 · 대본 Fable(없으면 무료 AI) · 그림 Gemini · 인물별 목소리</p>
  ${S.ai_images ? "" : `<div class="note">⚠️ AI 이미지가 꺼져 있어요</div>`}
  <div class="card"><div class="field" style="margin-top:0"><label>새 시리즈 — 한 줄 줄거리</label>
    <input id="stLog" maxlength="160" placeholder="예: 시골 소녀가 아무도 못 뽑던 바위 속 검을 뽑아버린다"></div>
    <div class="chips" id="stGenre">${GENRES.map((g, k) => `<button class="pill ${k ? "" : "accent"}" data-genre="${esc(g)}">${esc(g)}</button>`).join("")}</div>
    <button class="btn" id="stNew" style="margin-top:12px;width:100%">🎬 시리즈 만들고 1화 제작</button>
    <div class="m" style="margin-top:8px">인물 설정 → 인물 사진 → 1화 대본 → 장면 이미지 → 목소리·자막·음악 → 업로드 · 약 6~10분<br>
    오리지널 캐릭터만 써요(기존 작품 캐릭터는 저작권 문제로 제외)</div></div>
  <div class="section-title"><h2>내 시리즈 ${SS.length}개</h2></div>
  ${SS.length ? SS.map((b) => `<div class="card">
    <div class="row" style="padding:0"><div class="grow"><div class="t">${esc(b.title)}</div><div class="m">${esc(b.genre)} · ${b.episodes.length}화 제작 / 계획 ${b.planned}화</div></div>
      <button class="btn small" data-cmd="story next ${esc(b.slug)}" data-label="${esc(b.title)} 다음 화">▶ ${b.episodes.length + 1}화</button></div>
    <div class="m wrap" style="margin-top:6px">${esc(b.logline)}</div>
    <div class="cast">${b.characters.map((c) => `<div>${c.img ? `<img src="${imgUrl(c.img)}" alt="" loading="lazy">` : `<span class="noimg">🧑</span>`}<b>${esc(c.name)}</b><small>${esc(c.role)}</small></div>`).join("")}</div>
    ${b.episodes.length ? `<div class="eps">${b.episodes.map((e) => `<a class="ep" ${e.video ? `href="https://youtube.com/shorts/${encodeURIComponent(e.video)}" target="_blank" rel="noopener"` : ""}>
      <b>${e.n}화</b><span>${esc(e.title)}</span><small>${e.video ? "▶ 보기" : e.uploaded ? "" : "업로드 전"}</small></a>`).join("")}</div>` : ""}</div>`).join("")
    : empty("🎭", "아직 시리즈가 없어요", "한 줄 줄거리를 넣고 만들기를 누르면 1화까지 자동으로 만들어요")}`;
}

/* ───────── 화면: 영상 확인 ───────── */
function viewVideos() {
  if (D.empty) return `<div class="skeleton"></div>`;
  const V = D.videos || [], views = V.reduce((a, v) => a + v.views, 0);
  const best = V.slice().sort((a, b) => b.views - a.views)[0];
  const yid = (v) => encodeURIComponent(v.id);
  return `<h1 class="page">▶️ 영상 확인</h1><p class="sub">누르면 바로 재생 · 조회수는 매일 아침 갱신</p>
  <div class="kpis"><div class="card kpi"><div class="lbl">🎞️ 올린 영상</div><div class="num">${V.length}</div></div>
    <div class="card kpi"><div class="lbl">👀 총 조회수</div><div class="num">${views.toLocaleString()}</div></div></div>
  ${(D.previews || []).length ? `<div class="section-title"><h2>🆕 방금 만든 영상 (미리보기)</h2></div><div class="pv">${D.previews.map((p) => `
    <div class="pv-item"><video src="previews/${encodeURIComponent(p.file)}" controls playsinline preload="metadata"></video><div class="t clamp2">${esc(p.title)}</div><div class="m">${esc(p.date)}</div></div>`).join("")}</div>` : ""}
  ${best && best.views ? `<div class="card" style="margin-top:10px"><div class="m">🏆 최고 조회</div><div class="t">${esc(best.title)} · ${best.views.toLocaleString()}회</div></div>` : ""}
  ${V.length ? `<div class="vgrid">${V.map((v, k) => `<a class="vcard" href="https://youtube.com/shorts/${yid(v)}" target="_blank" rel="noopener noreferrer" data-video="${k}">
      <div class="thumb"><img loading="lazy" alt="" src="https://i.ytimg.com/vi/${yid(v)}/oardefault.jpg" data-fb="https://i.ytimg.com/vi/${yid(v)}/hqdefault.jpg">
      ${v.private ? '<span class="badge">🔒 비공개</span>' : ""}<span class="views">▶ ${v.views.toLocaleString()}</span></div>
      <div class="t clamp2">${esc(v.title)}</div><div class="m">❤ ${v.likes}${v.date ? " · " + esc(v.date.slice(5)) : ""}${v.channel === "new" ? " · F ai-LAB" : ""}</div></a>`).join("")}</div>`
    : empty("🎞️", "아직 올린 영상이 없어요", "영상제작에서 만들기를 눌러보세요", { attr: 'data-go="#make"', label: "🎬 영상 만들러 가기" })}
  <div class="btns"><a class="btn ghost" href="https://studio.youtube.com/" target="_blank" rel="noopener">📊 유튜브 스튜디오</a></div>`;
}

/* ───────── 화면: 파이프라인 (영상 외 자동화) ───────── */
function viewPipes() {
  if (D.empty) return `<div class="skeleton"></div>`;
  return `<h1 class="page">⚙️ 파이프라인</h1><p class="sub">영상 말고 다른 자동화 · 하고 싶은 일을 말하면 팀·스킬·일정까지 자동으로</p>
  <div class="quick">
    <button class="qbtn" data-cmd="daily" data-label="일일 자동운영"><span class="ico">⚙️</span>일일 자동운영</button>
    <button class="qbtn" data-cmd="blog" data-label="블로그 글"><span class="ico">📝</span>블로그 글</button>
    <button class="qbtn" data-cmd="news" data-label="정보 수집"><span class="ico">📰</span>트렌드 수집</button>
    <button class="qbtn" data-open="scout"><span class="ico">🔎</span>사업 발굴</button>
    <button class="qbtn" data-cmd="biz review" data-label="ROI 리뷰"><span class="ico">📊</span>ROI 리뷰</button>
    <button class="qbtn" data-open="addsite"><span class="ico">🌐</span>사이트 추가</button></div>
  ${(D.channels || []).length ? `<div class="section-title"><h2>올리는 곳</h2></div><div class="card">${D.channels.map((c) => `<div class="row">
    <span class="dot ${c.ready ? "" : "warn"}"></span><div class="grow"><div class="t">${esc(c.name)}</div><div class="m">${c.ready ? "자동 업로드 중" : esc(c.need || "")}</div></div></div>`).join("")}</div>` : ""}
  <div class="section-title"><h2>내 파이프라인</h2><button data-open="newpipe">＋ 만들기</button></div>
  ${(D.pipelines || []).length ? D.pipelines.map((pp) => `<div class="card"><div class="row"><div class="grow">
      <div class="t">${esc(pp.title)}</div><div class="m">${{ daily: "매일", weekly: "매주 월", manual: "수동" }[pp.schedule] || ""} · ${pp.steps.length}단계 · 실행 ${pp.runs}회${pp.enabled ? "" : " · 꺼짐"}</div>
      ${pp.viability ? `<div class="m">🧪 ${pp.viability.pass ? "생존" : "탈락"} · 흑자 확률 ${Math.round(pp.viability.sim.p_profit * 100)}%</div>` : ""}
      ${pp.upgraded_from ? `<div class="m">🔧 탈락한 파이프라인을 개선해서 만든 새 버전</div>` : ""}
      ${!pp.enabled && pp.disabled_reason ? `<div class="m">⏸ ${esc(pp.disabled_reason)}</div>` : ""}</div>
      <button class="btn small" data-cmd="pipeline run ${esc(pp.name)}" data-label="${esc(pp.title)}">▶ 실행</button></div>
      <div class="chips">${pp.steps.map((st) => `<span class="pill">${esc(st.command || st.agent)}</span>`).join("")}${(pp.skills_equipped || []).map((k) => `<span class="pill accent">⚡${esc(k.split("←")[1] || k)}</span>`).join("")}</div></div>`).join("")
    : empty("⚙️", "아직 파이프라인이 없어요", "하고 싶은 일을 말하면 팀·스킬·일정까지 알아서 만들어요", { attr: 'data-open="newpipe"', label: "＋ 파이프라인 만들기" })}`;
}

/* ───────── 화면: 더보기 ───────── */
function viewMore() {
  const item = (attr, ico, t, m) => `<div class="row tap" ${attr}><div class="score" style="font-size:20px">${ico}</div>
    <div class="grow"><div class="t">${t}</div><div class="m">${m}</div></div><span class="m">›</span></div>`;
  return `<h1 class="page">더보기</h1><div class="card">
    ${item('data-go="#biz"', "💼", "사업", "발굴 · 생존 테스트 · ROI")}
    ${item('data-go="#team"', "🧠", "팀", "에이전트 점수 · 자동 업그레이드")}
    ${item('data-go="#ai"', "🤖", "AI", "연결된 AI · 모델 점수 · AI 대결")}
    ${item('data-go="#reports"', "📄", "보고서", "매일 쌓이는 결과물")}</div>
  <div class="card">
    ${item('data-open="keys"', "🔑", "키 도우미", "API 키 이름 복사 · 발급 링크")}
    ${item('data-open="google"', "🔗", "구글 연결", "유튜브 · 블로그 1회 연결")}
    ${item('data-open="settings"', "⚙️", "설정", "토큰 · 테마")}</div>`;
}
function videoSheet(k) {
  const v = (D.videos || [])[+k]; if (!v) return "";
  const id = encodeURIComponent(v.id);
  return `<h3 class="wrap">${esc(v.title)}</h3><div class="chips">${v.private ? '<span class="pill candidate">🔒 비공개</span>' : '<span class="pill ok">공개</span>'}
    <span class="pill">▶ ${v.views.toLocaleString()}</span><span class="pill">❤ ${v.likes}</span>${v.date ? `<span class="pill">${esc(v.date)}</span>` : ""}</div>
    <div class="player${v.private ? " small" : ""}">${v.private ? `<div class="player-msg">🔒 비공개 영상은 앱 안에서 재생이 안 돼요<br>아래 버튼으로 유튜브 앱에서 보세요</div>`
      : `<iframe src="https://www.youtube-nocookie.com/embed/${id}?playsinline=1&rel=0" title="영상" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen loading="lazy"></iframe>`}</div>
    ${v.cover ? `<div class="note">🏷 표지 문구: ${esc(v.cover.replace(/\n/g, " / "))}</div>` : ""}
    <div class="btns"><a class="btn" href="https://youtube.com/shorts/${id}" target="_blank" rel="noopener">▶️ 유튜브 앱에서</a>
      <a class="btn ghost" href="https://studio.youtube.com/video/${id}/edit" target="_blank" rel="noopener">✏️ 스튜디오 수정</a></div>`;
}
const newChanSheet = () => `<h3>📺 새 채널 F ai-LAB 연결</h3><ol class="steps-ol">
  <li><a target="_blank" rel="noopener" href="https://www.youtube.com/channel_switcher">유튜브 채널 전환</a> → <b>채널 만들기</b> → 이름 <b>F ai-LAB</b></li>
  <li>PC에서 <b>C:\\link\\tools\\google_login\\google_login_youtube.bat</b> 더블클릭</li>
  <li>브라우저에서 <b>F ai-LAB</b> 선택 → 허용 → 끝 (다음 제작부터 새 채널에 공개)</li></ol>
  <p class="sub">연결 전엔 기존 채널에 비공개로만 올라가요</p>`;
const musicSheet = () => `<h3>🎵 배경음악·효과음 등록</h3><ol class="steps-ol">
  <li><a target="_blank" rel="noopener" href="https://studio.youtube.com/">유튜브 스튜디오</a> → 오디오 보관함 → <b>저작자 표시 필요 없음</b> 필터</li>
  <li>음악 10곡 → <b>C:\\link\\audio_src\\music</b>, 효과음 → <b>audio_src\\sfx</b> (이름에 whoosh·pop·ding 있으면 자리 맞춰 들어가요)</li>
  <li>PC에서 <b>C:\\link\\tools\\audio_pack\\audio_pack.bat</b> 더블클릭 → 자동 암호화·업로드</li></ol>
  <p class="sub">공개 저장소라 원본은 암호화해서 올려요 · 지금은 합성 효과음만 들어가요</p>`;

/* ───────── 화면: AI ───────── */
function viewAI() {
  if (D.empty) return `<div class="skeleton"></div>`;
  const days = D.budget.days, max = Math.max(...days.map((d) => d.usd), 0.0001);
  const total = days.reduce((a, d) => a + d.usd, 0);
  const conn = D.providers.filter((p) => p.connected).length;
  return `<h1 class="page">AI 통합</h1><p class="sub">${conn}/${D.providers.length}개 연결 · 무료 AI 먼저, 막히면 다음 AI로 자동 전환</p>
  <div class="card"><div class="row"><div class="grow"><div class="m">최근 14일 AI 비용</div>
    <div class="num" style="font-family:var(--display);font-size:22px;font-weight:800">${usd(total)}</div></div>
    <span class="pill accent">오늘 ${usd(D.budget.today)}</span></div>
    <div class="chart">${days.map((d) => `<div class="${d.usd ? "" : "zero"}" style="height:${Math.max(4, (d.usd / max) * 100)}%" title="${esc(d.d)} ${usd(d.usd)}"></div>`).join("")}</div>
    <div class="axis"><span>${esc(days[0].d.slice(5))}</span><span>오늘</span></div></div>
  <div class="section-title"><h2>🚀 자동 업로드</h2><button data-open="google">구글 연결 방법</button></div>
  <div class="card">${(D.channels || []).map((c) => `<div class="row"><span class="dot ${c.ready ? "" : "off"}"></span>
    <div class="grow"><div class="t">${esc(c.name)}</div><div class="m">${c.ready ? "자동 업로드 중" : esc(c.need)}</div></div></div>`).join("")}</div>
  <div class="section-title"><h2>연결된 AI</h2><button data-open="keys">🔑 키 발급 도우미</button></div>
  <button class="btn ghost" style="margin-bottom:10px" data-cmd="ai check" data-label="연결 점검">🩺 연결 점검 (AI마다 실제 호출해서 진단)</button>
  <div class="pgrid">${[...D.providers].sort((a, b) => b.connected - a.connected || b.free - a.free).map((p) => `
    <div class="card prov tap" data-prov="${esc(p.id)}"><span class="dot ${p.connected ? "" : "off"}"></span>
    <div class="grow"><div class="t">${esc(NAMES[p.id] || p.id)}</div><div class="m">${p.connected ? "연결됨" : "미연결"} · ${p.free ? "무료" : "유료"}</div></div></div>`).join("")}</div>
  <div class="section-title"><h2>정보 출처 ${(D.sources || []).filter((x) => !x.removed).length}곳</h2><button data-open="addsite">＋ 사이트 추가</button></div>
  <div class="card">${(D.sources || []).filter((x) => !x.removed).slice(0, 8).map((x) => `<div class="row"><div class="grow">
    <div class="t">${esc(x.name)}</div><div class="m">${esc(x.category)} · ${esc(x.origin)} · ${esc(x.added || "")}</div></div>
    ${x.origin !== "기본" ? '<span class="pill ok">자동 추가</span>' : ""}</div>`).join("") || '<div class="m">매일 자동으로 새 사이트를 찾아 추가해요</div>'}</div>
  <div class="section-title"><h2>모델 성적표</h2><button data-open="arena">AI 대결</button></div>
  ${D.models.length ? `<div class="card">${D.models.map((m) => `<div class="row"><div class="grow">
      <div class="t">${esc(m.model)}</div><div class="bar ${m.dropped ? "bad" : ""}"><i style="width:${m.avg * 10}%"></i></div></div>
      <div style="text-align:right"><b>${m.avg}</b><div class="m">${m.n}회</div></div>${m.dropped ? '<span class="pill bad">탈락</span>' : ""}</div>`).join("")}</div>`
    : empty("🏆", "아직 평가 기록이 없어요", "AI 대결을 돌리면 같은 문제로 채점해 순위를 매겨요", { attr: 'data-open="arena"', label: "⚔️ AI 대결 시작" })}`;
}

/* ───────── 화면: 보고서 ───────── */
function viewReports() {
  if (D.empty) return `<div class="skeleton"></div>`;
  const made = D.ideas.filter((i) => i.product);
  return `<h1 class="page">보고서</h1><p class="sub">결과만 깔끔하게 — 매일 자동으로 쌓여요</p>
  ${made.length ? `<div class="section-title"><h2>📦 만든 상품</h2></div><div class="card">${made.map((i) => `<div class="row tap" data-idea="${esc(i.id)}">
    <div class="score" style="font-size:17px">📕</div><div class="grow"><div class="t">${esc(i.product.title)}</div><div class="m">${esc(i.id)} · ${esc(i.platform)} · ${esc(i.product.made)}</div></div></div>`).join("")}</div>
    <div class="section-title"><h2>보고서</h2></div>` : ""}
  ${D.reports.length ? `<div class="card">${D.reports.map(reportRow).join("")}</div>` : empty("📄", "보고서가 아직 없어요", "일일 자동운영을 실행해 보세요", { attr: 'data-cmd="daily" data-label="일일 자동운영"', label: "⚙️ 지금 실행" })}`;
}
async function viewReport(file) {
  const v = $("#view");
  v.innerHTML = `<button class="back" data-go="#reports">‹ 보고서 목록</button><div class="skeleton"></div>`;
  try { v.innerHTML = `<button class="back" data-go="#reports">‹ 보고서 목록</button><article class="card md view-enter">${md(await fetchText(file))}</article>`; }
  catch { v.innerHTML += empty("😵", "보고서를 열 수 없어요", "잠시 후 다시 시도해 주세요"); }
}

/* ───────── 시트들 ───────── */
const commandSheet = () => `<h3>⚡ 무엇을 할까요?</h3><p class="sub" style="margin:0">CEO AI가 팀에 나눠서 처리하고 결과만 보고해요</p>
  <div class="field"><textarea id="goal" placeholder="예) 일본 BOOTH에서 팔 AI 프롬프트 템플릿 만들어줘"></textarea></div>
  <div class="suggest">${["미국 쇼츠 바이럴 공식 분석", "스마트스토어용 상품 3개 기획", "깃허브에서 쓸만한 마케팅 스킬 찾아 장착", "이번 주 수익 개선 계획"].map((s) =>
    `<button data-fill="${esc(s)}">${esc(s)}</button>`).join("")}</div>
  <div style="margin-top:16px"><button class="btn" id="goBtn">🚀 실행</button></div>`;
const scoutSheet = () => `<h3>🔎 사업 발굴</h3><p class="sub" style="margin:0">시장별로 30일 안에 첫 매출 가능한 사업을 찾아 채점해요</p>
  <div class="quick" style="margin-top:14px">${(D.markets || ["KR", "US", "JP", "GLOBAL"]).map((m) =>
    `<button class="qbtn" data-cmd="biz scout --market ${esc(m)}" data-label="${esc(m)} 사업 발굴"><span class="ico">${{ KR: "🇰🇷", US: "🇺🇸", JP: "🇯🇵" }[m] || "🌍"}</span>${esc(m)}</button>`).join("")}</div>`;
const logSheet = (id) => `<h3>💵 매출 · 비용 기록</h3>
  <div class="field"><label>사업</label><select id="lid">${D.ideas.filter((i) => i.status !== "killed").map((i) =>
    `<option value="${esc(i.id)}" ${i.id === id ? "selected" : ""}>${esc(i.id)} · ${esc(i.title)}</option>`).join("") || "<option value=''>진행 중인 사업 없음</option>"}</select></div>
  <div class="field"><label>종류</label><div class="seg" id="ltype"><button class="on" data-v="revenue">매출</button><button data-v="cost">비용</button></div></div>
  <div class="field"><label>금액</label><div style="display:grid;grid-template-columns:1fr 100px;gap:8px">
    <input id="lamt" type="number" inputmode="decimal" placeholder="30000"><select id="lcur"><option>KRW</option><option>USD</option><option>JPY</option><option>EUR</option></select></div></div>
  <div class="field"><label>메모 (선택)</label><input id="lnote" placeholder="첫 판매"></div>
  <div style="margin-top:16px"><button class="btn" id="logBtn">기록하기</button></div>`;
const newAgentSheet = () => `<h3>＋ 새 팀 만들기</h3><p class="sub" style="margin:0">CEO AI가 역할에 맞게 프롬프트와 도구를 설계해요</p>
  <div class="field"><label>팀 이름 (영문)</label><input id="aname" placeholder="tiktok_ops"></div>
  <div class="field"><label>하는 일</label><textarea id="adesc" placeholder="틱톡 계정 운영: 트렌드 분석, 대본, 해시태그"></textarea></div>
  <div style="margin-top:16px"><button class="btn" id="agentBtn">만들기</button></div>`;
const arenaSheet = () => `<h3>⚔️ AI 대결</h3><p class="sub" style="margin:0">연결된 모든 AI에게 같은 문제를 내고 Claude가 이름을 가린 채 채점해요. 낮은 점수의 AI는 자동 탈락</p>
  <div class="field"><textarea id="arenaTask" placeholder="예) 20대 대상 다이어트 쇼츠 훅 문장 5개"></textarea></div>
  <div style="margin-top:16px"><button class="btn" id="arenaBtn">대결 시작</button></div>`;
const addSiteSheet = () => `<h3>＋ 사이트 추가</h3><p class="sub" style="margin:0">일반 주소를 넣어도 RSS를 자동으로 찾아 검증 후 매일 수집해요. 새 사이트는 매일 자동으로도 추가되고, 일주일 계속 안 되면 자동으로 빠져요</p>
  <div class="field"><input id="siteUrl" type="url" inputmode="url" placeholder="https://example.com"></div>
  <div style="margin-top:16px"><button class="btn" id="siteBtn">추가하기</button></div>`;
const newPipeSheet = () => `<h3>⚙️ 파이프라인 만들기</h3><p class="sub" style="margin:0">하고 싶은 자동화를 말하면 단계 설계 → 필요한 팀 생성 → 깃허브에서 스킬 자동 장착 → 매일/매주 자동 실행까지 해요</p>
  <div class="field"><textarea id="pipeDesc" placeholder="예) 매일 미국 트렌드로 영어 숏츠 1개 만들어 올리고, 주간 성과 보고"></textarea></div>
  <div class="suggest">${["매일 트렌드로 블로그 글 1편 자동 게시", "매주 새 사업 발굴하고 상위 1개 상품까지 제작", "매일 숏츠 1개 제작·업로드하고 성과로 다음 대본 개선"].map((x) => `<button data-fill2="${esc(x)}">${esc(x)}</button>`).join("")}</div>
  <div style="margin-top:16px"><button class="btn" id="pipeBtn">만들기</button></div>`;
const googleSheet = () => `<h3>🔑 구글 1회 연결 (유튜브·블로그 자동 업로드)</h3>
  <div class="card" style="margin-top:8px"><div class="t">💻 PC에서 제일 쉬운 방법 (추천)</div><div class="note"><ol>
  <li><a target="_blank" rel="noopener" href="https://console.cloud.google.com/apis/library/youtube.googleapis.com">YouTube Data API</a>·<a target="_blank" rel="noopener" href="https://console.cloud.google.com/apis/library/blogger.googleapis.com">Blogger API</a> <b>사용</b></li>
  <li><a target="_blank" rel="noopener" href="https://console.cloud.google.com/auth/overview">동의 화면</a>: 외부 → 내 이메일 테스트 사용자 → <b>앱 게시</b></li>
  <li><a target="_blank" rel="noopener" href="https://console.cloud.google.com/auth/clients/create">OAuth 클라이언트</a>: <b>데스크톱 앱</b> → JSON 다운로드 → <b>client_secret.json</b></li>
  <li><a target="_blank" rel="noopener" href="https://github.com/${esc(REPO)}/archive/refs/heads/main.zip">프로그램 ZIP 받기</a> → <b>tools/google_login</b> 폴더에 client_secret.json 넣고 <b>google_login.bat</b> 더블클릭 → <b>허용</b></li>
  <li>나온 값 4개를 Secrets에 붙여넣기 (블로그 ID까지 자동으로 찾아줘요)</li></ol></div></div>
  <div class="m" style="margin:12px 2px 4px">또는 휴대폰만으로 (OAuth Playground):</div>
  <div class="note"><ol>
  <li><a target="_blank" rel="noopener" href="https://console.cloud.google.com/projectcreate">구글 클라우드</a>에서 새 프로젝트 → <b>YouTube Data API v3</b>, <b>Blogger API v3</b> 사용 설정</li>
  <li>OAuth 동의 화면: 외부 → 내 이메일을 테스트 사용자로 추가 → <b>게시 상태를 '프로덕션'</b>으로 (7일 만료 방지)</li>
  <li>사용자 인증 정보 → OAuth 클라이언트 ID → <b>웹 애플리케이션</b>, 리디렉션 URI: <b>https://developers.google.com/oauthplayground</b></li>
  <li><a target="_blank" rel="noopener" href="https://developers.google.com/oauthplayground">OAuth Playground</a> ⚙️ → Use your own OAuth credentials → ID·비밀번호 입력 → 범위에
   <b>https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/blogger</b>
   <button class="btn small ghost" data-copy="https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/blogger">범위 복사</button>
   입력 → Authorize → Exchange → <b>Refresh token</b> 복사</li>
  <li><a target="_blank" rel="noopener" href="https://github.com/${esc(REPO)}/settings/secrets/actions/new">Secrets</a>에 <b>GOOGLE_OAUTH_CLIENT_ID</b>, <b>GOOGLE_OAUTH_CLIENT_SECRET</b>, <b>GOOGLE_OAUTH_REFRESH_TOKEN</b>, <b>BLOGGER_BLOG_ID</b>(blogger.com 주소의 blogID 숫자) 저장</li>
  </ol>끝나면 매일 아침 자동으로 숏츠·블로그가 올라가요.</div>
  <button class="btn ghost" style="margin-top:10px" data-open="keys">🔑 키 이름 복사·붙여넣기 도우미</button>`;
const KEYS = [
  ["🚀 자동 업로드 (가장 중요 · ROI 0% 해결)", [
    ["GOOGLE_OAUTH_CLIENT_ID", "구글 1회 연결 ①", "#google"], ["GOOGLE_OAUTH_CLIENT_SECRET", "구글 1회 연결 ②", "#google"],
    ["GOOGLE_OAUTH_REFRESH_TOKEN", "구글 1회 연결 ③", "#google"], ["BLOGGER_BLOG_ID", "blogger.com 내 블로그 주소의 blogID 숫자", "https://www.blogger.com/"],
    ["YOUTUBE_OAUTH_REFRESH_TOKEN", "새 채널(F ai-LAB) 전용 · PC에서 google_login_youtube.bat 실행하면 자동 저장", "https://www.youtube.com/channel_switcher"]]],
  ["🆓 무료 AI (막히면 자동 전환)", [
    ["GEMINI_API_KEY", "Get API key → Create", "https://aistudio.google.com/apikey"], ["GROQ_API_KEY", "Create API Key", "https://console.groq.com/keys"],
    ["CEREBRAS_API_KEY", "API Keys → Generate", "https://cloud.cerebras.ai/"], ["OPENROUTER_API_KEY", "Create Key (무료 모델만 사용)", "https://openrouter.ai/settings/keys"],
    ["MISTRAL_API_KEY", "Create new key (무료 체험 등급)", "https://console.mistral.ai/api-keys"]]],
  ["🎬 영상 품질 (무료 · 추천)", [
    ["PEXELS_API_KEY", "고화질 세로 실사 영상 · 무료", "https://www.pexels.com/api/new/"],
    ["PIXABAY_API_KEY", "실사 영상 · 무료 (Pexels 신규 발급 중단 → 이것 추천)", "https://pixabay.com/api/docs/"],
    ["AUDIO_KEY", "배경음악·효과음 · PC에서 audio_pack.bat 실행하면 자동 저장 (유튜브 오디오 보관함)", "https://studio.youtube.com/"],
    ["POLLINATIONS_TOKEN", "무료 이미지 AI · 로고 없이·더 빠르게 (선택, 없어도 무료로 그림)", "https://auth.pollinations.ai/"],
    ["GEMINI_API_KEY", "AI 영상·이미지도 이 키로 만듦 (AI Studio에서 결제 연결해야 영상 가능 · 월 $5 한도)", "https://aistudio.google.com/usage"]]],
  ["⭐ 품질·분석 (선택)", [
    ["ANTHROPIC_API_KEY", "Claude · 유료 · 계획·검수 품질↑ (CLAUDE_API_KEY 이름도 인식)", "https://console.anthropic.com/settings/keys"],
    ["OPENAI_API_KEY", "ChatGPT · 유료 (CHATGPT_API_KEY 이름도 인식)", "https://platform.openai.com/api-keys"],
    ["YOUTUBE_API_KEY", "YouTube Data API v3 사용 → 사용자 인증 정보 → API 키", "https://console.cloud.google.com/apis/credentials"],
    ["GH_SEARCH_TOKEN", "스킬 자동 검색용 · Public repositories 읽기만", "https://github.com/settings/personal-access-tokens/new"]]],
];
const keysSheet = () => {
  const set = (D && D.keys_set) || {};
  const done = Object.values(set).filter(Boolean).length;
  return `<h3>🔑 키 발급 도우미</h3><p class="sub" style="margin:0">키마다 ① 발급 → ② 이름 복사 → ③ Secrets에 붙여넣기. 등록됨 ${done}/${Object.keys(set).length || 12}</p>
  ${KEYS.map(([group, rows]) => `<div class="section-title"><h2>${group}</h2></div><div class="card">${rows.map(([name, how, url]) => `
    <div class="row" style="flex-wrap:wrap"><span class="dot ${set[name] ? "" : "off"}"></span>
      <div class="grow"><div class="t" style="font-family:monospace;font-size:13px">${name}</div><div class="m wrap">${set[name] ? "✅ 등록됨" : esc(how)}</div></div>
      ${set[name] ? "" : `<div style="display:flex;gap:6px;width:100%;margin-top:8px">
        ${url.startsWith("#") ? `<button class="btn small ghost kb" data-open="google">① 방법</button>` : `<a class="btn small ghost kb" target="_blank" rel="noopener" href="${url}">① 발급</a>`}
        <button class="btn small ghost kb" data-copy="${name}">② 복사</button>
        <a class="btn small kb" target="_blank" rel="noopener" href="https://github.com/${esc(REPO)}/settings/secrets/actions/new">③ 넣기</a></div>`}</div>`).join("")}</div>`).join("")}
  <p class="note">발급 화면의 키 값은 ③에서 Secret 칸에 붙여넣으세요. 키 값은 채팅·메모에 남기지 마세요.</p>`;
};
const noTokenSheet = (text) => `<h3>실행하려면 한 번만 연결해 주세요</h3>
  <p class="note">명령 <b>“${esc(text)}”</b> 을(를) 복사했어요. 지금은 깃허브 앱에서 <b>Run workflow</b>를 눌러 실행할 수 있어요.</p>
  <a class="btn" style="display:block;text-align:center;margin-top:12px" target="_blank" rel="noopener" href="https://github.com/${esc(REPO)}/actions/workflows/mother.yml">깃허브에서 실행</a>
  <button class="btn ghost" style="margin-top:8px" data-open="settings">⚙️ 앱에서 바로 실행하도록 연결</button>`;
const settingsSheet = () => {
  const th = store.get("theme", "auto");
  return `<h3>⚙️ 설정</h3>
  <div class="field"><label>화면 테마</label><div class="seg" id="theme">${[["auto", "자동"], ["dark", "다크"], ["light", "라이트"]].map(([v, l]) =>
    `<button data-v="${v}" class="${th === v ? "on" : ""}">${l}</button>`).join("")}</div></div>
  <div class="field"><label>깃허브 토큰 (앱에서 바로 실행용 · 이 휴대폰에만 저장)</label>
    <input id="tok" type="password" autocomplete="off" placeholder="${token() ? "저장됨 ●●●●" : "github_pat_..."}"></div>
  <div class="btns"><button class="btn" id="tokSave">저장 · 연결 확인</button><button class="btn ghost" id="tokDel">토큰 삭제</button></div>
  <div class="note"><b>토큰 만들기(1분):</b><ol><li><a target="_blank" rel="noopener" href="https://github.com/settings/personal-access-tokens/new">새 토큰 만들기</a> 열기</li>
    <li>Repository access → <b>Only select</b> → <b>${esc(REPO.split("/")[1])}</b></li><li>Permissions → <b>Actions: Read and write</b></li><li>생성된 토큰을 위에 붙여넣기</li></ol></div>
  <div class="note"><b>홈 화면에 앱으로 추가:</b> 아이폰은 Safari 공유 버튼 → 홈 화면에 추가 · 안드로이드는 Chrome 메뉴 → 앱 설치</div>
  <div class="note">저장소: <a target="_blank" rel="noopener" href="https://github.com/${esc(REPO)}">${esc(REPO)}</a> · 데이터 ${ago(D && D.updated)}</div>`;
};
const tokenFixSheet = (code) => code === "401"
  ? `<h3>🔑 토큰이 맞지 않아요</h3><p class="note">토큰이 만료됐거나 잘못 복사됐어요. 새로 만들어 ⚙️ 설정에 다시 붙여넣어 주세요.</p>
     <button class="btn" style="margin-top:12px" data-open="settings">⚙️ 설정 열기</button>`
  : code === "403"
  ? `<h3>🔒 토큰 권한이 부족해요</h3><p class="note">토큰은 맞는데 <b>실행 권한</b>이 빠져 있어요. 토큰을 고치면 다시 붙여넣을 필요 없이 바로 돼요.</p>
     <div class="note"><ol><li><a target="_blank" rel="noopener" href="https://github.com/settings/personal-access-tokens">내 토큰 목록</a>에서 만든 토큰 누르기 → <b>Edit</b></li>
     <li>Repository access: <b>Only select repositories</b> → <b>${esc(REPO.split("/")[1])}</b> 선택</li>
     <li>Permissions → Repository permissions → <b>Actions: Read and write</b></li><li>맨 아래 <b>Update</b> → 앱에서 다시 실행</li></ol></div>`
  : `<h3>⚠️ 잠시 후 다시 시도해 주세요</h3><p class="note">깃허브 응답이 원활하지 않아요 (코드 ${esc(code)}).</p>`;
const provSheet = (id) => {
  const p = D.providers.find((x) => x.id === id);
  return `<h3>${esc(NAMES[id] || id)}</h3><div class="chips"><span class="pill ${p.connected ? "ok" : ""}">${p.connected ? "연결됨" : "미연결"}</span><span class="pill">${p.free ? "무료 등급" : "유료"}</span></div>
  <p class="note">${esc(p.note)}</p>${p.connected ? "" : keysSheet().replace("<h3>🔑 AI 키 넣는 법</h3>", "")}`;
};

/* ───────── 라우터 & 이벤트 ───────── */
function render() {
  const hash = location.hash || "#home";
  const tab = /^#(biz|team|ai|report)/.test(hash) ? "more" : hash === "#story" ? "make" : hash.slice(1);
  document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("on", tab === a.dataset.tab));
  if (!D) { $("#view").innerHTML = `<div class="skeleton"></div><div class="skeleton"></div>`; return; }
  if (hash.startsWith("#report=")) return viewReport(decodeURIComponent(hash.slice(8)));
  const quick = { "#cmd": commandSheet, "#google": googleSheet, "#keys": keysSheet };  // 홈 화면 아이콘 바로가기
  if (quick[hash]) { history.replaceState(null, "", "#home"); $("#view").innerHTML = `<div class="view-enter">${viewHome()}</div>`; return openSheet(quick[hash]()); }
  const v = { "#home": viewHome, "#make": viewMake, "#story": viewStory, "#videos": viewVideos, "#pipes": viewPipes, "#more": viewMore,
    "#biz": viewBiz, "#team": viewTeam, "#ai": viewAI, "#reports": viewReports }[hash] || viewHome;
  $("#view").innerHTML = `<div class="view-enter">${v()}</div>`;
}
const SHEETS = { newchan: newChanSheet, music: musicSheet, newpipe: newPipeSheet, google: googleSheet, addsite: addSiteSheet, scout: scoutSheet, log: logSheet, newagent: newAgentSheet, arena: arenaSheet, keys: keysSheet, settings: settingsSheet };

document.addEventListener("click", (e) => {
  const gb = e.target.closest("[data-genre]");
  if (gb) { gb.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("accent", b === gb)); return; }
  const vid = e.target.closest("[data-video]");
  if (vid && D) { e.preventDefault(); return openSheet(videoSheet(vid.dataset.video)); }
  const el = e.target.closest("[data-go],[data-cmd],[data-open],[data-idea],[data-cmdlog],[data-errlog],[data-filter],[data-fill],[data-fill2],[data-copy],[data-prov],[data-close],[data-v]");
  if (!el) return;
  const ds = el.dataset;
  if (ds.close !== undefined) return closeSheet();
  if (ds.go) { closeSheet(); location.hash = ds.go; return; }
  if (ds.cmd) return dispatch(ds.cmd, "", ds.label);
  if (ds.open) { if (D && !D.empty) openSheet(SHEETS[ds.open](ds.id)); else if (ds.open === "settings") openSheet(settingsSheet()); return; }
  if (ds.idea) return openSheet(ideaSheet(ds.idea));
  if (ds.errlog !== undefined) { const r = D.errors[+ds.errlog];
    return openSheet(`<h3>⚠️ ${esc(r.msg)}</h3><p class="sub" style="margin:0">${ago(r.ts)} · ${esc(r.cmd || "")}</p>
      <div class="field"><label>원문</label><div class="card md"><pre><code>${esc(r.error)}</code></pre></div></div>`); }
  if (ds.cmdlog !== undefined) { const c = D.commands[+ds.cmdlog];
    return openSheet(`<h3>${c.ok ? "✅" : "⚠️"} ${esc(cmdName(c.cmd))}</h3><p class="sub" style="margin:0">${ago(c.ts)} · ${esc(c.cmd)}</p>
      <div class="field"><div class="card md"><pre><code>${esc(c.output)}</code></pre></div></div>`); }
  if (ds.prov) return openSheet(provSheet(ds.prov));
  if (ds.filter) { bizFilter = ds.filter; return render(); }
  if (ds.fill) { $("#goal").value = ds.fill; return $("#goal").focus(); }
  if (ds.copy) { navigator.clipboard?.writeText(ds.copy).then(() => toast(`복사됨: ${ds.copy.slice(0, 40)}`), () => toast("복사 실패 — 길게 눌러 복사해 주세요")); return; }
  if (ds.fill2) { $("#pipeDesc").value = ds.fill2; return $("#pipeDesc").focus(); }
  if (ds.v) {
    el.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === el));
    if (el.parentElement.id === "theme") { store.set("theme", ds.v === "auto" ? "" : ds.v); applyTheme(); }
  }
});
document.addEventListener("click", async (e) => {
  const id = e.target.id;
  if (id === "goBtn") { const g = $("#goal").value.trim(); if (!g) return toast("할 일을 입력해 주세요"); dispatch("daily", g, "목표"); }
  if (id === "arenaBtn") { const g = $("#arenaTask").value.trim(); if (!g) return toast("문제를 입력해 주세요");
    dispatch(`ai arena ${q(g)}`, "", "AI 대결"); }
  if (id === "logBtn") {
    const iid = $("#lid").value, amt = parseFloat($("#lamt").value), cur = $("#lcur").value;
    const type = $("#ltype .on").dataset.v, note = $("#lnote").value.trim().slice(0, 60);
    if (!iid || !(amt > 0)) return toast("사업과 금액을 확인해 주세요");
    dispatch(`biz log ${iid} --${type} ${amt} --currency ${cur}${note ? " --note " + q(note) : ""}`, "", "매출 기록");
  }
  if (id === "stNew") {
    const lg = $("#stLog").value.trim(); if (!lg) return toast("한 줄 줄거리를 적어 주세요");
    const g = $("#stGenre .accent")?.dataset.genre || "";
    dispatch(`story new ${q(lg)}${g ? " --genre " + q(g) : ""}`, "", "새 AI 스토리 + 1화");
  }
  if (id === "vTest" || id === "vMake") {
    const t = $("#vTopic").value.trim();
    dispatch(`shorts${id === "vTest" ? " --private" : ""}${t ? " --topic " + q(t) : ""}`, "", id === "vTest" ? "영상 테스트 제작" : "영상 제작");
  }
  if (id === "pipeBtn") {
    const d = $("#pipeDesc").value.trim(); if (!d) return toast("하고 싶은 자동화를 적어 주세요");
    dispatch(`pipeline new ${q(d)}`, "", "파이프라인 만들기");
  }
  if (id === "siteBtn") {
    const u = $("#siteUrl").value.trim();
    if (!/^https:\/\/[^\s"]+$/.test(u)) return toast("https:// 로 시작하는 주소를 넣어 주세요");
    dispatch(`news add ${q(u)}`, "", "사이트 추가");
  }
  if (id === "agentBtn") {
    const n = $("#aname").value.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_"), d = $("#adesc").value.trim();
    if (!n || !d) return toast("이름과 하는 일을 입력해 주세요");
    dispatch(`agent new ${n} ${q(d)}`, "", "새 팀 만들기");
  }
  if (id === "tokSave") {
    const v = $("#tok").value.trim(); if (v) store.set("gh_token", v);
    if (!token()) return toast("토큰을 붙여넣어 주세요");
    // 실행 권한 확인: 없는 워크플로에 실행 요청 → 권한 있으면 404, 없으면 403 (실제 실행 안 됨)
    try { await gh(`/repos/${REPO}/actions/workflows/permission-probe.yml/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main" }) }); }
    catch (err) {
      const code = String(err.message).slice(0, 3);
      if (code === "404" || code === "422") { toast("✅ 연결 성공! 이제 앱에서 바로 실행돼요"); return closeSheet(); }
      return openSheet(tokenFixSheet(code));
    }
  }
  if (id === "tokDel") { store.set("gh_token", ""); toast("토큰을 삭제했어요"); closeSheet(); }
});
document.addEventListener("error", (e) => { const t = e.target; if (t.tagName !== "IMG" || !t.closest(".thumb")) return;
  if (t.dataset.fb) { t.src = t.dataset.fb; delete t.dataset.fb; } else t.remove(); }, true);
document.addEventListener("load", (e) => { const t = e.target;  // 유튜브의 '썸네일 없음' 회색 그림(120px)도 대체
  if (t.tagName === "IMG" && t.closest(".thumb") && t.naturalWidth <= 120) t.dispatchEvent(new Event("error")); }, true);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });
$("#fab").onclick = () => openSheet(commandSheet());
$("#settingsBtn").onclick = () => openSheet(settingsSheet());
$("#refreshBtn").onclick = () => load();
window.addEventListener("hashchange", () => { closeSheet(); window.scrollTo(0, 0); render(); });

function applyTheme() {
  const t = store.get("theme");
  t ? document.documentElement.setAttribute("data-theme", t) : document.documentElement.removeAttribute("data-theme");
}
applyTheme();
setInterval(() => { const c = $("#clock"); if (c) c.textContent = new Date().toTimeString().slice(0, 5); }, 15000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) load(true); });
if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("sw.js").catch(() => {});
render();
load(true);
if (token()) pollRun();
