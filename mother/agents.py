"""에이전트 = agents/<name>.yaml. 생성·실행·평가·자동 업그레이드."""
import yaml

from . import llm, store, tools

BASE_RULES = (
    "규칙: 결론부터, 군더더기 없이. 확인 안 된 수치는 '추정' 표기. 불법·약관위반·스팸·허위리뷰 수단은 제외하고 "
    "합법적 대안을 제시. 보고는 {lang}, 해외 시장용 산출물은 그 시장 언어로 작성."
)


def path(name):
    return store.AGENTS / f"{name}.yaml"


def load(name):
    return yaml.safe_load(path(name).read_text(encoding="utf-8"))


def save(spec):
    path(spec["name"]).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")


def all_agents():
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(store.AGENTS.glob("*.yaml"))}


def system_prompt(spec):
    parts = [spec["system"].strip(), BASE_RULES.format(lang=store.cfg()["report_lang"])]
    for sk in spec.get("skills", []):
        f = store.SKILLS / f"{sk}.md"
        if f.exists():
            parts.append(f"## 스킬: {sk}\n{f.read_text(encoding='utf-8')[:6000]}")
    return "\n\n".join(parts)  # 고정 텍스트만 → 캐시 적중 유지


last_model = {}  # 에이전트별 마지막 사용 모델 (평가 → 모델 성적표 연결)


def run(name, task, context=""):
    """무료 AI 우선 라우팅 → 실패 시 다음 AI → 마지막 Claude. 반환: 최종 텍스트."""
    from . import providers
    spec = load(name)
    user = f"{task}\n\n[참고자료]\n{context}" if context else task
    out, used, errs = "", None, []
    for p, m in providers.candidates(spec):
        try:
            if p == "anthropic":
                out = _run_claude(spec, user, m)
            else:
                out = providers.run_openai(p, m, system_prompt(spec), user, spec.get("tools", []), agent=name)
            if out:
                used = f"{p}:{m}"
                break
        except llm.BudgetExceeded:
            raise
        except Exception as e:  # 한도 초과·장애·모델 단종 → 다음 AI로 자동 전환
            errs.append(f"{p}: {str(e)[:120]}")
    last_model[name] = used
    store.append_jsonl("runs.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "agent": name, "model": used,
                                      "version": spec.get("version", 1), "task": task[:300], "output": out[:1500],
                                      "failover": errs})
    if not out and not errs:
        raise RuntimeError(llm.NO_KEY)
    return out or "[실패] " + " / ".join(errs)


def _run_claude(spec, user, model=None):
    name = spec["name"]
    b = store.cfg()["budget"]
    tdefs = tools.claude_tools(spec.get("tools", []))
    messages = [{"role": "user", "content": user}]
    resp = None
    for turn in range(b["max_tool_turns"]):
        resp = llm.call(spec.get("tier", "worker"), system_prompt(spec), messages, tools=tdefs or None,
                        agent=name, model=model)
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        if resp.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for blk in resp.content:
            if blk.type != "tool_use":
                continue
            try:
                out, err = tools.run_tool(blk.name, blk.input), False
            except Exception as e:  # 도구 실패는 모델에게 알려 스스로 우회하게 함
                out, err = f"error: {e}", True
            results.append({"type": "tool_result", "tool_use_id": blk.id, "content": out, "is_error": err})
        if turn == b["max_tool_turns"] - 2:
            results.append({"type": "text", "text": "도구 사용 한도에 도달. 지금까지 정보로 최종 결과를 작성하라."})
        messages.append({"role": "user", "content": results})
    return llm.text_of(resp) if resp else ""


# ───────────────────────── 생성 ─────────────────────────
SPEC_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["name", "title", "tier", "model", "tools", "system", "skill_query"],
    "properties": {
        "name": {"type": "string", "description": "영문 소문자_밑줄"},
        "title": {"type": "string"},
        "tier": {"type": "string", "enum": ["worker", "mother"]},
        "model": {"type": "string", "description": "'auto'(무료 AI 우선 자동) 또는 'provider:model'. 특별한 이유 없으면 auto"},
        "tools": {"type": "array", "items": {"type": "string", "enum": ["web_search", *tools.REGISTRY]}},
        "system": {"type": "string", "description": "역할·절차·출력형식을 담은 간결한 시스템 프롬프트(300자 내외)"},
        "skill_query": {"type": "string", "description": "이 역할에 도움 될 깃허브 SKILL.md 영어 검색어 2~3단어"},
    },
}


def create(name, description):
    spec = llm.ask_json("mother", "너는 AI 회사의 CTO다. 새 직원(에이전트) 명세를 설계한다. 프롬프트는 짧고 구체적으로.",
                        f"이름: {name}\n역할 설명: {description}\n가장 적은 도구로 목표를 달성하도록 설계.",
                        SPEC_SCHEMA, agent="cto")
    query = spec.pop("skill_query", "")
    spec.update(name=name, version=1, skills=[])
    save(spec)
    from . import skills_finder
    sk = skills_finder.equip(name, query)  # 새 팀마다 맞는 스킬(프롬프트) 자동 장착
    if sk:
        spec = load(name)
    return spec


# ───────────────────────── 평가 & 업그레이드 ─────────────────────────
def score(name, avg_window=None):
    w = avg_window or store.cfg()["agent_review"]["window"]
    rows = [r for r in store.read_jsonl("scores.jsonl") if r["agent"] == name][-w:]
    return (sum(r["score"] for r in rows) / len(rows), rows) if rows else (None, [])


UPGRADE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["system", "tools", "changelog"],
    "properties": {"system": {"type": "string"},
                   "tools": SPEC_SCHEMA["properties"]["tools"],
                   "changelog": {"type": "string"}},
}


def upgrade(name, force=False):
    avg, rows = score(name)
    if avg is None or (avg >= store.cfg()["agent_review"]["min_avg_score"] and not force):
        return None
    spec = load(name)
    fb = "\n".join(f"- ({r['score']}) {r['feedback']}" for r in rows)
    new = llm.ask_json("mother", "너는 프롬프트 엔지니어다. 피드백을 반영해 에이전트를 개선한다. 더 짧고 정확하게.",
                       f"현재 프롬프트:\n{spec['system']}\n현재 도구: {spec.get('tools')}\n최근 평가(평균 {avg:.1f}):\n{fb}",
                       UPGRADE_SCHEMA, agent="prompt_engineer")
    hist = store.AGENTS / "_history"
    hist.mkdir(exist_ok=True)
    (hist / f"{name}.v{spec.get('version', 1)}.yaml").write_text(
        yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    spec.update(system=new["system"], tools=new["tools"], version=spec.get("version", 1) + 1)
    spec.setdefault("changelog", []).append(f"v{spec['version']} {store.today()}: {new['changelog']}")
    save(spec)
    return spec
