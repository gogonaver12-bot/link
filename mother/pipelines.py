"""파이프라인 자동 생성기: 하고 싶은 일 한 줄 → 단계 설계 · 필요한 팀(에이전트) 생성 · 스킬 자동 장착 · 일정 등록 · 자동 실행."""
import contextlib
import io
import re
import shlex

import yaml

from . import agents, llm, skills_finder, store

PIPES = store.ROOT / "pipelines"
PIPES.mkdir(exist_ok=True)
COMMANDS = {  # 파이프라인이 쓸 수 있는 내장 명령 (이 목록 밖은 실행 안 함)
    "make": "make <사업ID> — 사업 아이디어로 판매용 상품(원고·PDF·판매페이지) 제작",
    "biz scout": "biz scout --market KR|US|JP|GLOBAL — 사업 발굴",
    "biz review": "biz review — 수익률 판정(확장/개선/탈락)",
    "news": "news — 트렌드 수집 / news discover — 새 정보 사이트 추가",
    "shorts": "shorts — 숏츠 대본→영상→유튜브 업로드(구글 연결 시)",
    "blog": "blog — 블로그 글 작성→Blogger 게시(구글 연결 시)",
    "agent upgrade": "agent upgrade — 저성과 팀 프롬프트 개선",
}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["name", "title", "schedule", "steps", "new_agents", "skill_queries"],
    "properties": {
        "name": {"type": "string", "description": "영문 소문자_밑줄"},
        "title": {"type": "string"},
        "schedule": {"type": "string", "enum": ["daily", "weekly", "manual"]},
        "steps": {"type": "array", "description": "2~6단계", "items": {
            "type": "object", "additionalProperties": False, "required": ["kind", "agent", "task", "command"],
            "properties": {"kind": {"type": "string", "enum": ["agent", "command"]},
                           "agent": {"type": "string", "description": "kind=agent 일 때 팀 이름, 아니면 빈칸"},
                           "task": {"type": "string", "description": "kind=agent 일 때 지시 한두 문장, 아니면 빈칸"},
                           "command": {"type": "string", "description": "kind=command 일 때 내장 명령, 아니면 빈칸"}}}},
        "new_agents": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["name", "description", "skill_query"],
            "properties": {"name": {"type": "string"}, "description": {"type": "string"},
                           "skill_query": {"type": "string", "description": "이 팀에 맞는 깃허브 SKILL.md 영어 검색어 2~3단어"}}}},
        "skill_queries": {"type": "array", "items": {"type": "string"}, "description": "기존 팀에 더 붙일 스킬 영어 검색어 0~2개"},
    },
}


def _safe(name):
    return re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")[:40] or "pipeline"


def path(name):
    return PIPES / f"{_safe(name)}.yaml"


def load(name):
    return yaml.safe_load(path(name).read_text(encoding="utf-8"))


def save(p):
    path(p["name"]).write_text(yaml.safe_dump(p, allow_unicode=True, sort_keys=False), encoding="utf-8")


def all_pipes():
    return [yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted(PIPES.glob("*.yaml"))]


def allowed(cmd):
    return any(cmd.strip().startswith(k) for k in COMMANDS)


def create(description):
    team = "\n".join(f"- {n}: {s.get('title', '')}" for n, s in agents.all_agents().items())
    spec = llm.ask_json(
        "mother", "너는 AI 회사의 자동화 설계자다. 사람 손이 가지 않는 반복 파이프라인을 최소 단계로 설계한다. "
        "있는 팀과 내장 명령을 우선 쓰고, 꼭 필요할 때만 새 팀을 만든다. 불법·약관 위반·스팸 단계는 넣지 않는다.",
        f"만들 자동화: {description}\n\n현재 팀:\n{team}\n\n내장 명령:\n" + "\n".join(f"- {v}" for v in COMMANDS.values()),
        SCHEMA, agent="pipeline_architect")
    spec["name"] = _safe(spec["name"])
    made, equipped = [], []
    for na in spec["new_agents"]:
        n = _safe(na["name"])
        if not agents.path(n).exists():
            agents.create(n, na["description"])
            made.append(n)
        sk = skills_finder.equip(n, na.get("skill_query", ""))
        if sk:
            equipped.append(f"{n}←{sk}")
    steps = []
    for st in spec["steps"]:
        if st["kind"] == "command":
            if allowed(st["command"]):
                steps.append({"command": st["command"].strip()})
        else:
            a = _safe(st["agent"])
            steps.append({"agent": a if agents.path(a).exists() else "researcher", "task": st["task"]})
    targets = list(dict.fromkeys(s["agent"] for s in steps if "agent" in s))
    for q in spec["skill_queries"][:2]:
        for a in targets[:1]:
            sk = skills_finder.equip(a, q)
            if sk:
                equipped.append(f"{a}←{sk}")
    pipe = {"name": spec["name"], "title": spec["title"], "description": description, "schedule": spec["schedule"],
            "enabled": True, "created": store.today(), "steps": steps, "agents_created": made, "skills_equipped": equipped, "runs": []}
    save(pipe)
    try:  # 만들자마자 생존 테스트 → 탈락하면 꺼둠
        from . import viability
        pipe, _ = viability.test_pipeline(pipe["name"])
    except llm.BudgetExceeded:
        raise
    except Exception:
        pass
    return pipe


def _command(cmd):
    from . import __main__ as cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            cli.main(shlex.split(cmd))
        except SystemExit as e:
            print(f"종료: {e}")
    return buf.getvalue().strip()


def run(name):
    p = load(name)
    ctx, log, h = "", [], store.cfg()["budget"]["handoff_chars"]
    for st in p["steps"]:
        try:
            if "command" in st:
                out = _command(st["command"]) if allowed(st["command"]) else "허용되지 않은 명령"
                label = st["command"]
            else:
                out = agents.run(st["agent"], st["task"], ctx)
                label = f"{st['agent']}: {st['task'][:60]}"
        except llm.BudgetExceeded as e:
            log.append(("중단", str(e)))
            break
        except Exception as e:  # 한 단계 실패해도 다음 단계 진행
            out, label = f"[실패] {type(e).__name__}: {str(e)[:200]}", st.get("command") or st.get("agent")
        log.append((label, out))
        ctx = (ctx + f"\n## {label}\n{out}")[-h:]
    p["runs"] = (p.get("runs", []) + [{"date": store.today(), "ok": all(not o.startswith("[실패]") for _, o in log)}])[-20:]
    save(p)
    rp = store.REPORTS / f"{store.now():%Y%m%d-%H%M}-파이프라인-{p['name']}.md"
    rp.write_text(f"# 파이프라인: {p['title']}\n\n" + "\n\n".join(f"### {l}\n{o[:3000]}" for l, o in log) + "\n", encoding="utf-8")
    return log


def run_due():
    """daily 는 매일, weekly 는 월요일에 자동 실행."""
    done = []
    for p in all_pipes():
        if not p.get("enabled") or p["schedule"] == "manual":
            continue
        if p["schedule"] == "weekly" and store.now().weekday() != 0:
            continue
        if any(r["date"] == store.today() for r in p.get("runs", [])):
            continue
        log = run(p["name"])
        done.append(f"{p['title']} ({len(log)}단계)")
    return done
