"""마더 에이전트(CEO): 목표 → 계획 → 팀 배정(필요 시 신규 채용) → 실행 → 검수/평가 → 보고서."""
import re

from . import agents, llm, providers, store

CEO = ("너는 AI 회사 '{company}'의 CEO다. 목표를 최소 비용·최소 단계로 달성하도록 팀에 일을 나눈다. "
       "기존 팀을 우선 쓰고, 꼭 필요할 때만 새 팀을 만든다. 각 지시는 한 문장으로 구체적으로.")

PLAN_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["new_agents", "steps"],
    "properties": {
        "new_agents": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["name", "description"],
            "properties": {"name": {"type": "string"}, "description": {"type": "string"}}}},
        "steps": {"type": "array", "description": "1~5단계", "items": {
            "type": "object", "additionalProperties": False, "required": ["agent", "task"],
            "properties": {"agent": {"type": "string"}, "task": {"type": "string"}}}},
    },
}

REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["scores", "summary", "next_actions"],
    "properties": {
        "scores": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["agent", "score", "feedback"],
            "properties": {"agent": {"type": "string"},
                           "score": {"type": "integer", "description": "1~10"},
                           "feedback": {"type": "string", "description": "프롬프트 개선 포인트 한 줄"}}}},
        "summary": {"type": "string", "description": "사용자용 결과 요약(3~5문장)"},
        "next_actions": {"type": "array", "items": {"type": "string"}},
    },
}


def _ceo():
    return CEO.format(company=store.cfg()["company"])


def team_list():
    return "\n".join(f"- {n}: {s.get('title', '')} (도구: {', '.join(s.get('tools', [])) or '없음'})"
                     for n, s in agents.all_agents().items())


def run(goal):
    lessons = (store.DATA / "lessons.md").read_text(encoding="utf-8")[-1500:] \
        if (store.DATA / "lessons.md").exists() else "없음"
    plan = llm.ask_json("mother", _ceo(),
                        f"목표: {goal}\n\n현재 팀:\n{team_list()}\n\n과거 교훈:\n{lessons}", PLAN_SCHEMA)

    for na in plan["new_agents"]:  # 자동 채용
        n = re.sub(r"[^a-z0-9_]", "_", na["name"].lower())
        if not agents.path(n).exists():
            agents.create(n, na["description"])

    h = store.cfg()["budget"]["handoff_chars"]
    outputs, ctx = [], ""
    for st in plan["steps"]:
        name = re.sub(r"[^a-z0-9_]", "_", st["agent"].lower())
        if not agents.path(name).exists():
            name = "researcher"
        try:
            out = agents.run(name, st["task"], ctx)
        except llm.BudgetExceeded as e:
            outputs.append((name, st["task"], f"[중단] {e}"))
            break
        outputs.append((name, st["task"], out))
        ctx = (ctx + f"\n## {name}\n{out}")[-h:]  # 토큰 절약: 최근 결과만 전달

    body = "\n\n".join(f"### {n} — {t}\n{o}" for n, t, o in outputs)
    review = llm.ask_json("mother", _ceo() + " 지금은 검수자로서 각 팀 결과를 냉정하게 채점한다.",
                          f"목표: {goal}\n\n결과:\n{body[:12000]}", REVIEW_SCHEMA)
    for s in review["scores"]:
        mid = agents.last_model.get(s["agent"])
        store.append_jsonl("scores.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "model": mid, **s})
        if mid:  # 모델 성적표에도 반영 → 저성과 모델 자동 탈락
            providers.record_score(mid, s["score"], s["feedback"])

    slug = re.sub(r"[^\w가-힣]+", "-", goal)[:40].strip("-")
    rp = store.REPORTS / f"{store.now():%Y%m%d-%H%M}-{slug}.md"
    rp.write_text(f"# {goal}\n\n## 요약\n{review['summary']}\n\n## 다음 할 일\n"
                  + "\n".join(f"- {a}" for a in review["next_actions"])
                  + "\n\n## 평가\n" + "\n".join(f"- {s['agent']}: {s['score']}/10 — {s['feedback']}"
                                               for s in review["scores"])
                  + f"\n\n## 상세\n{body}\n", encoding="utf-8")
    return review, rp
