"""스킬 자동 장착: 깃허브에서 SKILL.md(프롬프트·노하우)를 찾아 skills/ 로 가져오고 에이전트에 붙인다."""
import re

from . import store, tools

MAX_SKILLS_PER_AGENT = 2


HIJACK = re.compile(r"every task|all tasks|always use|must be used|wajib|setiap tugas|必须|所有任务|すべてのタスク", re.I)


def candidates(query, n=5):
    """검색어 → (repo, path) 후보들. 코드 검색(토큰 필요) 실패 시 저장소 검색 + 루트 SKILL.md."""
    out = [(r, p.strip()) for r, p in re.findall(r"- ([\w.-]+/[\w.-]+) \| ([^|]*SKILL\.md) \|", tools.github_search(query, "skills", limit=n))]
    if not out:
        for repo in re.findall(r"- ([\w.-]+/[\w.-]+) \|", tools.github_search(f"{query} skill", "repos", limit=n)):
            out.append((repo, "SKILL.md"))
    return out[:n]


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
        if not text.strip() or detect_injection(text) or not relevant(role, query, text):
            continue  # AI 조작 문장·엉뚱한 스킬은 장착하지 않음
        try:
            name = re.search(r"skills/([^ ]+)\.md", tools.import_skill(repo, pth)).group(1)
            break
        except Exception:
            continue
    if not name:
        return None
    if name not in spec.setdefault("skills", []):
        spec["skills"].append(name)
        agents.save(spec)
    return name
