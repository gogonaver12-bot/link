"""API 키 없이 돌아가는 검증 테스트:  python -m pytest -q"""
import json
import shutil
import types

import pytest

from mother import agents, business, llm, mother, store, tools


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    for name in ("DATA", "REPORTS", "WORKSPACE", "SKILLS"):
        d = tmp_path / name.lower()
        d.mkdir()
        monkeypatch.setattr(store, name, d)
    ag = tmp_path / "agents"
    shutil.copytree(store.ROOT / "agents", ag, ignore=shutil.ignore_patterns("_history"))
    monkeypatch.setattr(store, "AGENTS", ag)


def U(i=1000, o=500, cr=0):
    return types.SimpleNamespace(input_tokens=i, output_tokens=o, cache_creation_input_tokens=0,
                                 cache_read_input_tokens=cr, server_tool_use=None)


def test_cost_and_budget(monkeypatch):
    assert llm.cost_usd("claude-opus-5-5", U(1_000_000, 0)) == pytest.approx(4.0)
    store.append_jsonl("usage.jsonl", {"ts": store.now().isoformat(), "usd": 99})
    with pytest.raises(llm.BudgetExceeded):
        llm.call("worker", "s", [{"role": "user", "content": "x"}])


def test_tools_schema_and_sandbox(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    names = [t["name"] for t in tools.claude_tools(["web_search", "crawl", "youtube_search"])]
    assert names == ["crawl", "web_search"]  # 키 없는 youtube는 제외
    assert "저장됨" in tools.save_file("a/b.txt", "hi")
    with pytest.raises(ValueError):
        tools.save_file("../../evil.txt", "x")
    with pytest.raises(ValueError):
        tools.crawl("http://127.0.0.1/")


def test_agent_tool_loop(monkeypatch):
    calls = []

    def fake_call(tier, system, messages, tools=None, **k):
        calls.append(messages)
        if len(calls) == 1:
            blk = types.SimpleNamespace(type="tool_use", id="t1", name="save_file",
                                        input={"path": "x.md", "content": "대본"})
            return types.SimpleNamespace(stop_reason="tool_use", content=[blk])
        return types.SimpleNamespace(stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text="완료")])

    monkeypatch.setattr(llm, "call", fake_call)
    assert agents.run("content_creator", "쇼츠 대본") == "완료"
    assert (store.WORKSPACE / "x.md").read_text(encoding="utf-8") == "대본"
    assert calls[1][-1]["content"][0]["type"] == "tool_result"


def test_mother_run_creates_agent_and_report(monkeypatch):
    def fake_json(tier, system, prompt, schema, agent="mother", **k):
        if "steps" in schema["properties"]:
            return {"new_agents": [{"name": "Tiktok Ops", "description": "틱톡 운영"}],
                    "steps": [{"agent": "researcher", "task": "조사"}, {"agent": "tiktok_ops", "task": "운영"}]}
        if "scores" in schema["properties"]:
            return {"scores": [{"agent": "researcher", "score": 4, "feedback": "출처 부족"}],
                    "summary": "요약", "next_actions": ["A"]}
        return {"name": "x", "title": "틱톡팀", "tier": "worker", "tools": ["web_search"], "system": "틱톡"}

    monkeypatch.setattr(llm, "ask_json", fake_json)
    monkeypatch.setattr(agents, "run", lambda n, t, c="": f"{n} 결과")
    review, rp = mother.run("틱톡 수익화")
    assert agents.path("tiktok_ops").exists()
    assert "researcher: 4/10" in rp.read_text(encoding="utf-8")
    assert agents.score("researcher")[0] == 4


def test_business_cycle(monkeypatch):
    ideas = [{"id": "I0001", "title": "A", "market": "US", "platform": "Gumroad", "status": "active",
              "started": "2026-01-01", "score": 80},
             {"id": "I0002", "title": "B", "market": "KR", "platform": "크몽", "status": "active",
              "started": "2026-01-01", "score": 70}]
    store.save_json("ideas.json", ideas)
    business.log("I0001", revenue=300, cost=100)            # ROI +200% → scale
    business.log("I0002", revenue=10000, cost=100000, currency="KRW")  # ROI -90% → kill
    monkeypatch.setattr(llm, "ask_json", lambda *a, **k: {"items": [
        {"id": "I0001", "plan": "광고 확대", "lesson": ""}, {"id": "I0002", "plan": "", "lesson": "단가 낮음"}]})
    rows, _ = business.review()
    acts = {it["id"]: act for it, m, act in rows}
    assert acts == {"I0001": "scale", "I0002": "kill"}
    assert "단가 낮음" in (store.DATA / "lessons.md").read_text(encoding="utf-8")
    assert {i["id"]: i["status"] for i in store.load_json("ideas.json", [])}["I0002"] == "killed"


def test_score_weights():
    assert business.total({k: 100 for k in business.CRITERIA}) == 100
