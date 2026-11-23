"""사업 파이프라인: 발굴(scout) → 채점 → 승인 → 매출/비용 기록 → ROI 리뷰 → 확장/업그레이드/탈락 → 교훈 축적."""
import datetime as dt

from . import agents, llm, store

CRITERIA = {"demand": 0.25, "low_competition": 0.15, "low_cost": 0.15,
            "speed_to_revenue": 0.2, "scalability": 0.15, "low_risk": 0.1}

IDEA_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["ideas"],
    "properties": {"ideas": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["title", "market", "platform", "model", "first_step", "evidence", "scores"],
        "properties": {
            "title": {"type": "string"}, "market": {"type": "string"}, "platform": {"type": "string"},
            "model": {"type": "string", "description": "수익 구조(판매/구독/광고/외주 등)"},
            "first_step": {"type": "string", "description": "오늘 바로 할 첫 행동"},
            "evidence": {"type": "string", "description": "근거(트렌드/수요 지표/URL)"},
            "scores": {"type": "object", "additionalProperties": False, "required": list(CRITERIA),
                       "properties": {k: {"type": "integer", "description": "0~100"} for k in CRITERIA}},
        }}}},
}


def _ideas():
    return store.load_json("ideas.json", [])


def total(scores):
    return round(sum(scores[k] * w for k, w in CRITERIA.items()), 1)


def scout(market_code=None, n=3):
    c = store.cfg()
    markets = [m for m in c["markets"] if not market_code or m["code"] == market_code.upper()]
    lessons = (store.DATA / "lessons.md").read_text(encoding="utf-8")[-1500:] \
        if (store.DATA / "lessons.md").exists() else "없음"
    ideas, new = _ideas(), []
    for m in markets:
        research = agents.run("researcher", (
            f"{m['code']} 시장({m['lang']})에서 1인+AI가 30일 안에 첫 매출 가능한 온라인 사업 {n}개를 찾아라. "
            f"플랫폼 후보: {', '.join(m['platforms'])}. 최근 수요 증거(검색량/판매순위/바이럴)를 웹검색으로 확인. "
            f"과거 실패 교훈 반영:\n{lessons}"))
        got = llm.ask_json("worker", "리서치 결과를 사업 아이디어 JSON으로 정리하고 냉정하게 0~100 채점.",
                           research, IDEA_SCHEMA, agent="idea_scorer")["ideas"]
        for it in got:
            it.update(id=f"I{len(ideas) + len(new) + 1:04d}", score=total(it["scores"]),
                      status="candidate", created=store.today())
            new.append(it)
    ideas += new
    k = c["business"]["auto_approve_top"]
    for it in sorted(new, key=lambda x: -x["score"])[:k]:
        if it["score"] >= c["business"]["min_idea_score"]:
            it["status"] = "active"
            it["started"] = store.today()
    store.save_json("ideas.json", ideas)
    return new


def approve(idea_id):
    ideas = _ideas()
    for it in ideas:
        if it["id"] == idea_id:
            it.update(status="active", started=store.today())
    store.save_json("ideas.json", ideas)


def log(idea_id, revenue=0.0, cost=0.0, currency="USD", note=""):
    store.append_jsonl("ledger.jsonl", {"date": store.today(), "id": idea_id, "revenue_usd": store.to_usd(revenue, currency),
                                        "cost_usd": store.to_usd(cost, currency), "note": note})


def metrics(idea):
    rows = [r for r in store.read_jsonl("ledger.jsonl") if r["id"] == idea["id"]]
    rev = sum(r["revenue_usd"] for r in rows)
    cost = sum(r["cost_usd"] for r in rows)
    roi = (rev - cost) / cost if cost else (1.0 if rev else 0.0)
    age = (dt.date.today() - dt.date.fromisoformat(idea.get("started", store.today()))).days
    return {"revenue": round(rev, 2), "cost": round(cost, 2), "profit": round(rev - cost, 2),
            "roi": round(roi, 3), "age": age}


def decide(m):
    b = store.cfg()["business"]
    if m["age"] >= b["kill_after_days"] and m["roi"] <= b["kill_roi"]:
        return "kill"
    if m["roi"] >= b["target_roi"] and m["revenue"] > 0:
        return "scale"
    if m["age"] < 7:
        return "watch"
    return "upgrade"


ACTION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "plan", "lesson"],
        "properties": {"id": {"type": "string"},
                       "plan": {"type": "string", "description": "scale/upgrade: 이번 주 실행 계획 3줄"},
                       "lesson": {"type": "string", "description": "kill: 다음 발굴에 쓸 교훈 한 줄"}}}}},
}


def review():
    ideas = _ideas()
    rows, need = [], []
    for it in ideas:
        if it["status"] != "active":
            continue
        m = metrics(it)
        act = decide(m)
        rows.append((it, m, act))
        if act != "watch":
            need.append(f"{it['id']} [{act}] {it['title']} ({it['market']}/{it['platform']}) {m}")
    plans = {}
    if need:  # LLM 호출은 결정이 필요한 것만 1회로 묶어서
        out = llm.ask_json("mother", "너는 투자심사역이다. 숫자 근거로 간결하게.", "\n".join(need), ACTION_SCHEMA,
                           agent="investor")
        plans = {x["id"]: x for x in out["items"]}
    for it, m, act in rows:
        p = plans.get(it["id"], {})
        it["last_review"] = {"date": store.today(), "action": act, **m, "plan": p.get("plan", "")}
        if act == "kill":
            it["status"] = "killed"
            with (store.DATA / "lessons.md").open("a", encoding="utf-8") as f:
                f.write(f"- {store.today()} {it['title']}({it['market']}): {p.get('lesson', 'ROI 미달')}\n")
    store.save_json("ideas.json", ideas)
    return rows, plans
