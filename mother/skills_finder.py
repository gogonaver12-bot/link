"""스킬 자동 장착: 깃허브에서 SKILL.md(프롬프트·노하우)를 찾아 skills/ 로 가져오고 에이전트에 붙인다."""
import re

from . import store, tools

MAX_SKILLS_PER_AGENT = 2


HIJACK = re.compile(r"every task|all tasks|always use|must be used|wajib|setiap tugas|必须|所有任务|すべてのタスク", re.I)


TRUSTED = ("anthropics/", "vercel-labs/", "microsoft/", "obra/", "google/", "openai/", "github/")  # 공식·검증된 출처
MIN_INSTALLS = 100  # 설치 수 100 미만은 보류 (1,000 이상 우선)


def skills_sh(query, n=5):
    """skills.sh(스킬 디렉터리) 검색 → 설치 수·공식 출처 순으로 정렬. [{source, skillId, installs}]"""
    import requests
    try:
        r = requests.get("https://skills.sh/api/search", params={"q": query}, timeout=15, headers={"User-Agent": tools.UA})
        rows = r.json().get("skills", []) if r.ok else []
    except Exception:
        return []
    rows = [x for x in rows if x.get("installs", 0) >= MIN_INSTALLS or x.get("source", "").startswith(TRUSTED)]
    rows.sort(key=lambda x: (not x.get("source", "").startswith(TRUSTED), x.get("installs", 0) < 1000, -x.get("installs", 0)))
    return rows[:n]


def _skill_paths(row):
    sid = row["skillId"]
    return [f"skills/{sid}/SKILL.md", f"{sid}/SKILL.md", f".claude/skills/{sid}/SKILL.md", f"plugins/{sid}/SKILL.md", "SKILL.md"]


def candidates(query, n=5):
    """검색어 → (repo, path) 후보들. 1순위 skills.sh(설치 수·공식 출처), 2순위 깃허브 코드 검색, 3순위 저장소 검색 + 루트 SKILL.md."""
    out = []
    for row in skills_sh(query, n):
        for p in _skill_paths(row):
            out.append((row["source"], p))
    out += [(r, p.strip()) for r, p in re.findall(r"- ([\w.-]+/[\w.-]+) \| ([^|]*SKILL\.md) \|", tools.github_search(query, "skills", limit=n))]
    if not out:
        for repo in re.findall(r"- ([\w.-]+/[\w.-]+) \|", tools.github_search(f"{query} skill", "repos", limit=n)):
            out.append((repo, "SKILL.md"))
    return out[: n * 5]


def find_skill(query):
    c = candidates(query, 1)
    return c[0] if c else None


def _description(text):
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    return (m.group(1) if m else text[:400]).strip().strip('"')


def relevant(role, query, text):
    """엉뚱한 스킬 거르기: 언어(한/영만)·장악형(모든 작업에 쓰라는 라우터)·크기·관련성 검사."""
    desc = _description(text)
    if len(text) > 20000 or HIJACK.search(desc):
        return False
    han = len(re.findall(r"[\u4e00-\u9fff]", desc))
    if han > 10 and not re.search(r"[가-힣]", desc):  # 중국어 전용 스킬 제외
        return False
    words = [w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in {"skill", "the", "and", "for", "with"}]
    try:  # 무료 AI로 관련성 판정 (캐시, 토큰 소량)
        from . import providers
        ans, _ = providers.complete(f"팀 역할: {role}\n스킬 설명: {desc[:600]}\n이 스킬이 이 팀의 일(한국어·영어 작업)에 직접 도움이 되면 YES, 아니면 NO. 한 단어만.",
                                    system="YES 또는 NO만 답한다.", agent="skill_judge")
        return ans.strip().upper().startswith("YES")
    except Exception:
        return any(w in desc.lower() for w in words)


def equip(agent_name, query):
    """에이전트에 맞는 스킬을 찾아 가져와서 붙인다. 반환: 붙인 스킬 이름 또는 None."""
    from . import agents
    if not query or not agents.path(agent_name).exists():
        return None
    spec = agents.load(agent_name)
    if len(spec.get("skills", [])) >= MAX_SKILLS_PER_AGENT:
        return None
    from .collector import detect_injection
    role = f"{spec.get('title', agent_name)}: {spec.get('system', '')[:200]}"
    name = None
    for repo, pth in candidates(query):
        try:
            text = tools.github_read(repo, pth, 20001)
        except Exception:
            continue
        if not text.lstrip().startswith(("---", "#")) or "404: Not Found" in text[:40]:
            continue  # 그 경로에 스킬 파일이 없음 → 다음 경로
        if not text.strip() or detect_injection(text) or not relevant(role, query, text):
            continue  # AI 조작 문장·엉뚱한 스킬은 장착하지 않음
        try:
            name = re.search(r"skills/([^ ]+)\.md", tools.import_skill(repo, pth)).group(1)
            break
        except Exception:
            continue
    if not name:
        name = write_skill(role, query)  # 밖에서 맞는 스킬을 못 찾으면 직접 만듦 (Superpowers writing-skills 규칙)
    if not name:
        return None
    if name not in spec.setdefault("skills", []):
        spec["skills"].append(name)
        agents.save(spec)
    return name


def write_skill(role, query):
    """writing-skills 규칙: name(소문자-하이픈), description은 'Use when …'(언제 쓰는지만), 본문은 개요·언제 쓰나·절차·흔한 실수·검증.
    반환: 저장한 스킬 이름 또는 None."""
    from . import providers
    guide = (store.SKILLS / "superpowers-writing-skills.md")
    rules = guide.read_text(encoding="utf-8")[:4000] if guide.exists() else ""
    prompt = (f"역할: {role}\n필요한 스킬: {query}\n\n위 규칙대로 이 역할이 '{query}' 일을 잘하게 돕는 SKILL.md 하나를 써라. "
              "맨 위 YAML 머리말(name: 소문자-하이픈, description: 'Use when ...'로 언제 쓰는지만 한 문장), 본문은 한국어로 "
              "## 개요 / ## 언제 쓰나 / ## 절차(번호) / ## 흔한 실수 / ## 끝났는지 확인 — 400~900자, 사실만, 과장·불법·약관 위반 금지.")
    try:
        text, used = providers.complete(prompt, system=("너는 에이전트 스킬 작성자다. 규칙:\n" + rules)[:6000], agent="skill_writer")
    except Exception:
        return None
    m = re.search(r"---\s*\nname:\s*([a-z0-9-]+)", text)
    if not m or "description:" not in text:
        return None
    name = "co-" + m.group(1)[:50]
    body = text[text.index("---"):]
    (store.SKILLS / f"{name}.md").write_text(f"<!-- source: 회사 자체 작성(writing-skills 규칙, {used}, {store.today()}) -->\n{body}\n",
                                            encoding="utf-8")
    return name
