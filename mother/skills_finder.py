"""스킬 자동 장착: 깃허브에서 SKILL.md(프롬프트·노하우)를 찾아 skills/ 로 가져오고 에이전트에 붙인다."""
import re

from . import store, tools

MAX_SKILLS_PER_AGENT = 2


def find_skill(query):
    """검색어 → (repo, path) 1개. 코드 검색(토큰 필요) 실패 시 저장소 검색 + 루트 SKILL.md 시도."""
    res = tools.github_search(query, "skills", limit=5)
    m = re.search(r"- ([\w.-]+/[\w.-]+) \| ([^|]*SKILL\.md) \|", res)
    if m:
        return m.group(1), m.group(2).strip()
    res = tools.github_search(f"{query} skill", "repos", limit=5)
    for repo in re.findall(r"- ([\w.-]+/[\w.-]+) \|", res):
        try:
            if tools.github_read(repo, "SKILL.md", 200).strip():
                return repo, "SKILL.md"
        except Exception:
            continue
    return None


def equip(agent_name, query):
    """에이전트에 맞는 스킬을 찾아 가져와서 붙인다. 반환: 붙인 스킬 이름 또는 None."""
    from . import agents
    if not query or not agents.path(agent_name).exists():
        return None
    spec = agents.load(agent_name)
    if len(spec.get("skills", [])) >= MAX_SKILLS_PER_AGENT:
        return None
    try:
        hit = find_skill(query)
        if not hit:
            return None
        msg = tools.import_skill(*hit)
        name = re.search(r"skills/([^ ]+)\.md", msg).group(1)
    except Exception:
        return None
    text = (store.SKILLS / f"{name}.md").read_text(encoding="utf-8")
    from .collector import detect_injection
    if detect_injection(text):  # AI 조작 문장이 있는 스킬은 장착하지 않음
        (store.SKILLS / f"{name}.md").unlink(missing_ok=True)
        return None
    if name not in spec.setdefault("skills", []):
        spec["skills"].append(name)
        agents.save(spec)
    return name
