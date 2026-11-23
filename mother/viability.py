"""생존 테스트: 인터넷 조사 → AI 경쟁 추정(낙관·비관·중립) → 몬테카를로 수익 시뮬레이션 → 통과한 것만 살린다.

나중에 실제 매출이 쌓이면 각 AI의 예측과 비교해 '잘 맞힌 AI'만 살아남게 점수를 매긴다(모델 성적표).
"""
import json
import math
import random
import statistics
import zlib

from . import agents, llm, providers, store

PARAMS = {
    "type": "object", "additionalProperties": False,
    "required": ["price_usd", "conv_rate_pct", "visitors_low", "visitors_high", "ramp_days", "setup_cost_usd",
                 "unit_cost_pct", "monthly_cost_usd", "competition", "risks", "evidence"],
    "properties": {
        "price_usd": {"type": "number", "description": "건당 판매가(또는 광고면 1,000회 조회당 수익) USD"},
        "conv_rate_pct": {"type": "number", "description": "방문자→구매 전환율 %(광고형이면 100)"},
        "visitors_low": {"type": "number", "description": "자리 잡은 뒤 하루 방문/조회 수 비관치"},
        "visitors_high": {"type": "number", "description": "자리 잡은 뒤 하루 방문/조회 수 낙관치"},
        "ramp_days": {"type": "number", "description": "유입이 자리 잡기까지 걸리는 일수"},
        "setup_cost_usd": {"type": "number"},
        "unit_cost_pct": {"type": "number", "description": "플랫폼 수수료 등 매출 대비 %"},
        "monthly_cost_usd": {"type": "number"},
        "competition": {"type": "string", "enum": ["low", "mid", "high"]},
        "risks": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}, "description": "근거(가격·판매량·검색량, URL 포함)"},
    },
}
PERSONAS = [("중립 심사역", "근거로만 보수적으로 추정한다."),
            ("비관 분석가", "실패 이유를 먼저 찾고 낮게 잡는다."),
            ("낙관 분석가", "잘 될 경우를 현실 범위 안에서 잡는다.")]
COMP = {"low": 1.15, "mid": 0.85, "high": 0.55}


def _cfg():
    return {"min_p_profit": 0.4, "min_roi_p50": 0.3, "days": 90, "runs": 2000, "max_ais": 3, **store.cfg().get("viability", {})}


# ───────────────────────── 1. 인터넷 조사 ─────────────────────────
def research(subject):
    from . import collector
    task = (f"다음 사업/자동화의 수익 가능성을 인터넷으로 확인하라: {subject}\n"
            "경쟁 상품 가격대·판매량(리뷰 수)·검색 수요·실패 사례를 찾아 숫자와 출처 URL 위주로 10줄 이내로 보고.")
    try:
        found = agents.run("researcher", task, "관련 최근 소식:\n" + collector.search(subject.split()[0] if subject else "", limit=8))
    except llm.BudgetExceeded:
        raise
    except Exception as e:
        found = f"[조사 실패] {e}"
    return found[:4000]


# ───────────────────────── 2. AI 경쟁 추정 ─────────────────────────
def _estimators():
    out = [(p, m) for p, m in providers.candidates({"tier": "worker", "tools": []})]
    seen, uniq = set(), []
    for p, m in out:  # AI 회사별 1개씩 (서로 다른 AI끼리 경쟁)
        if p not in seen:
            seen.add(p)
            uniq.append((p, m))
    return uniq[:_cfg()["max_ais"]]


def _ask(p, m, system, prompt):
    if p == "anthropic":
        return llm.ask_json("worker", system, prompt, PARAMS, agent="estimator")
    body = {"model": m, "response_format": {"type": "json_object"}, "messages": [
        {"role": "system", "content": f"{system}\n반드시 이 JSON 스키마의 객체만 출력:\n{json.dumps(PARAMS, ensure_ascii=False)}"},
        {"role": "user", "content": prompt}]}
    d = providers._post(providers.cfgp()[p]["base"].rstrip("/") + "/chat/completions", providers._headers(p), body)
    providers._log(p, m, "estimator", d.get("usage") or {})
    t = d["choices"][0]["message"]["content"]
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


def compete(subject, evidence):
    ests = []
    for k, (p, m) in enumerate(_estimators()):
        role, rule = PERSONAS[k % len(PERSONAS)]
        try:
            e = _ask(p, m, f"너는 {role}다. {rule} 1인+AI 온라인 사업의 수익 변수를 추정한다.",
                     f"대상: {subject}\n\n인터넷 조사 결과:\n{evidence}\n\n위 근거로 수익 변수를 추정하라. 근거 없는 낙관 금지.")
            ests.append({"model": f"{p}:{m}", "role": role, **e})
        except llm.BudgetExceeded:
            raise
        except Exception:
            continue
    return ests


def aggregate(ests):
    if not ests:
        raise RuntimeError("추정에 참여한 AI가 없어요 (AI 키 확인)")
    num = [k for k, v in PARAMS["properties"].items() if v["type"] == "number"]
    agg = {k: statistics.median(float(e.get(k, 0) or 0) for e in ests) for k in num}
    agg["competition"] = statistics.mode(e.get("competition", "mid") for e in ests)
    agg["risks"] = list(dict.fromkeys(r for e in ests for r in e.get("risks", [])))[:6]
    agg["evidence"] = list(dict.fromkeys(r for e in ests for r in e.get("evidence", [])))[:6]
    spread = [abs(math.log(max(e["visitors_high"], 1) / max(agg["visitors_high"], 1))) for e in ests]
    agg["disagreement"] = round(max(spread), 2)  # AI끼리 의견 차이가 크면 불확실성↑
    return agg


# ───────────────────────── 3. 몬테카를로 시뮬레이션 ─────────────────────────
def simulate(pr, days=None, runs=None, seed=0):
    days, runs = days or _cfg()["days"], runs or _cfg()["runs"]
    rng = random.Random(seed)
    lo, hi = max(0.1, pr["visitors_low"]), max(pr["visitors_low"] + 0.1, pr["visitors_high"])
    unc = 0.5 + pr.get("disagreement", 0)
    rois, revs30, revs, be = [], [], [], []
    for _ in range(runs):
        steady = math.exp(rng.uniform(math.log(lo), math.log(hi))) * COMP.get(pr["competition"], 0.85) * rng.lognormvariate(0, 0.3)
        conv = max(0.0, pr["conv_rate_pct"] / 100 * rng.lognormvariate(0, unc))
        ramp = max(1, pr["ramp_days"] * rng.uniform(0.7, 1.6))
        rev = cost = 0.0
        cost += pr["setup_cost_usd"]
        r30, b = 0.0, None
        for t in range(1, days + 1):
            lam = steady * min(1.0, t / ramp) * conv
            sales = _poisson(rng, lam)
            day_rev = sales * pr["price_usd"] if pr["conv_rate_pct"] < 100 else steady * min(1.0, t / ramp) / 1000 * pr["price_usd"]
            rev += day_rev
            cost += day_rev * pr["unit_cost_pct"] / 100 + pr["monthly_cost_usd"] / 30
            if t == 30:
                r30 = rev
            if b is None and rev > cost:
                b = t
        rois.append((rev - cost) / cost if cost > 0 else (1.0 if rev > 0 else 0.0))
        revs.append(rev)
        revs30.append(r30)
        be.append(b or days + 1)
    q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(p * len(xs)))]
    return {"days": days, "runs": runs, "p_profit": round(sum(r > 0 for r in rois) / runs, 3),
            "roi_p10": round(q(rois, .1), 2), "roi_p50": round(q(rois, .5), 2), "roi_p90": round(q(rois, .9), 2),
            "rev30_p50": round(q(revs30, .5), 1), "rev_p10": round(q(revs, .1), 1), "rev_p50": round(q(revs, .5), 1),
            "rev_p90": round(q(revs, .9), 1), "breakeven_p50": q(be, .5)}


def _poisson(rng, lam):
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, int(rng.gauss(lam, math.sqrt(lam)) + 0.5))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def verdict(sim):
    c = _cfg()
    ok = sim["p_profit"] >= c["min_p_profit"] and sim["roi_p50"] >= c["min_roi_p50"]
    why = f"흑자 확률 {sim['p_profit']:.0%} · 90일 ROI 중앙값 {sim['roi_p50']:+.0%} (기준 {c['min_p_profit']:.0%}·{c['min_roi_p50']:+.0%})"
    return ok, why


# ───────────────────────── 4. 생존 테스트 ─────────────────────────
def test(subject, seed=0):
    evidence = research(subject)
    ests = compete(subject, evidence)
    params = aggregate(ests)
    sim = simulate(params, seed=seed)
    ok, why = verdict(sim)
    return {"date": store.today(), "pass": ok, "why": why, "sim": sim, "params": params, "evidence": evidence[:1500],
            "estimates": [{k: e.get(k) for k in ("model", "role", "price_usd", "conv_rate_pct", "visitors_low", "visitors_high")} for e in ests]}


def test_idea(idea_id, kill=True):
    ideas = store.load_json("ideas.json", [])
    idea = next(i for i in ideas if i["id"] == idea_id)
    res = test(f"{idea['title']} ({idea.get('market')}/{idea.get('platform')}, {idea.get('model')})", seed=zlib.crc32(idea_id.encode()))
    idea["viability"] = res
    store.append_jsonl("estimates.jsonl", {"date": store.today(), "id": idea_id, "rev30_p50": res["sim"]["rev30_p50"],
                                           "estimates": res["estimates"]})
    if not res["pass"] and kill and idea["status"] in ("active", "candidate"):
        idea["status"] = "killed"
        idea["killed_by"] = "생존 테스트"
        with (store.DATA / "lessons.md").open("a", encoding="utf-8") as f:
            f.write(f"- {store.today()} {idea['title']}({idea.get('market')}): 시뮬레이션 탈락 — {res['why']}; 위험: {', '.join(res['params']['risks'][:2])}\n")
    store.save_json("ideas.json", ideas)
    return idea, res


def test_pipeline(name):
    from . import pipelines
    p = pipelines.load(name)
    res = test(f"자동화 파이프라인: {p['title']} — {p.get('description', '')} / 단계: "
               + ", ".join(s.get("command") or s.get("agent") for s in p["steps"]), seed=zlib.crc32(name.encode()))
    p["viability"] = {k: res[k] for k in ("date", "pass", "why", "sim")}
    if not res["pass"]:
        p["enabled"] = False
        p["disabled_reason"] = "생존 테스트 탈락: " + res["why"]
    pipelines.save(p)
    return p, res


def calibrate(idea, actual_rev30):
    """30일 실제 매출과 각 AI의 예측을 비교 → 잘 맞힌 AI가 살아남도록 모델 성적표에 반영."""
    rows = [r for r in store.read_jsonl("estimates.jsonl") if r["id"] == idea["id"]]
    if not rows:
        return
    for e in rows[-1]["estimates"]:
        steady = math.sqrt(max(e["visitors_low"] or 0.1, 0.1) * max(e["visitors_high"] or 0.1, 0.1))
        pred = steady * (e["conv_rate_pct"] or 0) / 100 * (e["price_usd"] or 0) * 20  # 첫 30일(유입 형성기) 근사
        err = abs(math.log((pred + 1) / (actual_rev30 + 1)))
        providers.record_score(e["model"], max(1, round(10 - err * 3)), f"{idea['id']} 30일 예측 {pred:.0f} vs 실제 {actual_rev30:.0f}",
                               source="calibration")


def test_all(limit=None):
    out = []
    ideas = [i for i in store.load_json("ideas.json", []) if i["status"] in ("active", "candidate")]
    for i in ideas[:limit or len(ideas)]:
        try:
            _, r = test_idea(i["id"])
            out.append(f"{'✅ 생존' if r['pass'] else '❌ 탈락'} {i['id']} {i['title'][:30]} — {r['why']}")
        except llm.BudgetExceeded:
            raise
        except Exception as e:
            out.append(f"⚠️ {i['id']} 테스트 실패: {str(e)[:100]}")
    from . import pipelines
    for p in pipelines.all_pipes():
        if not p.get("enabled"):
            continue
        try:
            _, r = test_pipeline(p["name"])
            out.append(f"{'✅ 생존' if r['pass'] else '❌ 탈락'} 파이프라인 {p['title'][:30]} — {r['why']}")
        except llm.BudgetExceeded:
            raise
        except Exception as e:
            out.append(f"⚠️ 파이프라인 {p['name']} 테스트 실패: {str(e)[:100]}")
    return out
