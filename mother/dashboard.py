"""휴대폰 앱용 스냅샷: data/dashboard.json 하나에 모든 현황을 모은다 (키 값은 절대 포함하지 않음)."""
import datetime as dt
import json
import os

from . import agents, business, providers, store


def _report_list():
    out = []
    for p in sorted(store.REPORTS.rglob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:40]:
        first = p.read_text(encoding="utf-8").splitlines()[:1]
        out.append({"file": str(p.relative_to(store.ROOT)), "title": (first[0].lstrip("# ") if first else p.stem)[:80],
                    "date": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat(timespec="minutes")})
    return out


def build():
    c = store.cfg()
    usage = store.read_jsonl("usage.jsonl")
    today = dt.date.today()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    spend = {d: 0.0 for d in days}
    by_model = {}
    for r in usage:
        if r["ts"][:10] in spend:
            spend[r["ts"][:10]] += r["usd"]
        by_model[r.get("model", "?")] = by_model.get(r.get("model", "?"), 0) + r["usd"]

    ideas = []
    for i in store.load_json("ideas.json", []):
        ideas.append({k: i.get(k) for k in ("id", "title", "market", "platform", "model", "first_step", "evidence",
                                            "scores", "score", "status", "created", "started", "last_review")}
                     | {"metrics": business.metrics(i) if i.get("started") else None})
    ledger = store.read_jsonl("ledger.jsonl")
    rev, cost = sum(r["revenue_usd"] for r in ledger), sum(r["cost_usd"] for r in ledger)

    team = []
    for n, s in agents.all_agents().items():
        avg, rows = agents.score(n)
        team.append({"name": n, "title": s.get("title", n), "version": s.get("version", 1), "tools": s.get("tools", []),
                     "model": s.get("model", "auto"), "skills": s.get("skills", []),
                     "avg": round(avg, 1) if avg is not None else None, "evals": len(rows),
                     "last_feedback": rows[-1]["feedback"] if rows else ""})

    provs = [{"id": p, "free": bool(pc.get("free")), "note": pc.get("note", ""),
              "connected": bool(os.getenv(pc["key"])) if pc.get("key") else providers.available(p)}
             for p, pc in c["providers"].items()]
    models = [{"model": m, "avg": a, "n": n, "dropped": providers.demoted(m)}
              for m, (a, n) in sorted(providers.model_stats().items(), key=lambda x: -x[1][0])]

    jobs_file = store.ROOT / "jarvis" / "jobs.json"
    done = set(store.load_json("jobs_done.json", []))
    jobs = [{"id": j["id"], "task": j["task"], "done": j["id"] in done}
            for j in (json.loads(jobs_file.read_text(encoding="utf-8")) if jobs_file.exists() else [])]

    snap = {
        "updated": store.now().isoformat(timespec="seconds"),
        "company": c["company"],
        "repo": os.getenv("GITHUB_REPOSITORY", "gogonaver12-bot/link"),
        "budget": {"daily": c["budget"]["daily_usd"], "today": round(spend.get(today.isoformat(), 0), 4),
                   "days": [{"d": d, "usd": round(spend[d], 4)} for d in days],
                   "by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda x: -x[1])[:8]}},
        "money": {"revenue": round(rev, 2), "cost": round(cost, 2), "profit": round(rev - cost, 2)},
        "ideas": ideas,
        "team": team,
        "providers": provs,
        "models": models,
        "markets": [m["code"] for m in c["markets"]],
        "reports": _report_list(),
        "runs": [{k: r.get(k) for k in ("ts", "agent", "model", "task")} for r in store.read_jsonl("runs.jsonl")[-12:]][::-1],
        "errors": [{k: r.get(k) for k in ("ts", "cmd", "error")} for r in store.read_jsonl("errors.jsonl")[-5:]][::-1],
        "jobs": jobs[-10:],
    }
    (store.DATA / "dashboard.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return snap
