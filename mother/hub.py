"""통합 허브: 회사의 스킬·프롬프트·에이전트를 한곳에서 찾고(통합 검색), 모든 Claude Code 세션이 쓰도록 .claude/ 로 묶는다.

- find(q): 이미 있는 것(skills/·prompts/·agents/) → skills.sh 추천(설치 수·공식 출처) → 깃허브 → 웹 순서로 한 번에 검색
- sync_claude(): skills/*.md → .claude/skills/<이름>/SKILL.md, agents/*.yaml → .claude/agents/<이름>.md, skills/INDEX.md 목록
  (이 저장소를 여는 모든 세션 — 클라우드·PC(C:\\link)·앱 — 이 같은 스킬과 에이전트를 자동으로 씀)
"""
import re

import yaml

from . import store

ROOT = store.ROOT
OTHER_REPOS = {  # 다른 저장소의 프롬프트는 사용자 승인(2026-11-26)으로 prompts/<저장소>/ 에 통합됨
    "gogonaver12-bot/jarvis-ai-hub": "→ prompts/jarvis-ai-hub/ (프롬프트 슬롯·토큰 절약 프리셋·ChatGPT 연구·Codex 구현)",
    "gogonaver12-bot/JARVIS-VIDEO-FACTORY": "→ prompts/jarvis-video-factory/ (에이전트 규칙·Gemini 규칙·프롬프트 DNA)",
    "gogonaver12-bot/ai-collaboration-starter": "→ prompts/ai-collaboration-starter/ (웹 채팅용 복사 프롬프트·AI별 규칙)",
    "gogonaver12-bot/jarvis": "→ mother/skillscore.py (훅 채점기, 이미 통합)",
    "gogonaver12-bot/JARVIS-DOT-COMPANY-RPG": "프롬프트 파일 없음",
}


def _front(text):
    m = re.match(r"\s*(?:<!--.*?-->\s*)*---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def _first_line(text):
    for ln in text.splitlines():
        ln = ln.strip().lstrip("#").strip()
        if ln and not ln.startswith(("<!--", "---")):
            return ln[:160]
    return ""


def local_assets():
    out = []
    for f in sorted(store.SKILLS.glob("*.md")):
        if f.name == "INDEX.md":
            continue
        t = f.read_text(encoding="utf-8")
        fm = _front(t)
        out.append({"kind": "스킬", "name": f.stem, "desc": str(fm.get("description") or _first_line(t))[:300], "path": f"skills/{f.name}", "text": t})
    for f in sorted((ROOT / "prompts").rglob("*.md")):  # prompts/<저장소>/… 까지 (다른 저장소에서 통합한 것 포함)
        t = f.read_text(encoding="utf-8")
        rel = f.relative_to(ROOT / "prompts")
        name = f.stem if len(rel.parts) == 1 else f"{rel.parts[0]}-{f.stem}"
        out.append({"kind": "프롬프트", "name": name, "desc": _first_line(t), "path": f"prompts/{rel.as_posix()}", "text": t})
    for f in sorted((ROOT / "agents").glob("*.yaml")):
        s = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        out.append({"kind": "에이전트", "name": f.stem, "desc": f"{s.get('title', f.stem)} — {str(s.get('system', ''))[:160]}",
                    "path": f"agents/{f.name}", "text": str(s.get("system", "")) + " " + " ".join(s.get("skills", []) + s.get("tools", []))})
    return out


def _score(q, a):
    words = [w for w in re.split(r"[\s,/·]+", q.lower()) if len(w) > 1]
    hay_head = (a["name"] + " " + a["desc"]).lower()
    hay = a["text"].lower()
    return sum(3 * (w in hay_head) + min(hay.count(w), 3) for w in words)


def find(q, remote=True):
    lines = [f"# 🔎 통합 검색: {q}", ""]
    loc = sorted(((_score(q, a), a) for a in local_assets()), key=lambda x: -x[0])
    loc = [a for s, a in loc if s > 0][:8]
    lines.append("## 📦 이미 있는 것 (바로 사용)")
    lines += [f"- [{a['kind']}] **{a['name']}** — {a['desc'][:120]} (`{a['path']}`)" for a in loc] or ["- 없음"]
    if remote:
        from . import skills_finder, tools
        rows = skills_finder.skills_sh(q, 5)
        lines += ["", "## 🌐 skills.sh 추천 (공식 출처 → 설치 수 순)"]
        lines += [f"- **{r['skillId']}** · {r['source']} · 설치 {r.get('installs', 0):,}회 → 에이전트에 붙이기: `agent add-skill <에이전트> \"{q}\"`"
                  for r in rows] or ["- 없음"]
        try:
            gh = tools.github_search(q, "skills", limit=3)
            lines += ["", "## 🐙 깃허브 스킬·프롬프트", gh.strip()[:1200] or "- 없음"]
        except Exception as e:
            lines += ["", f"## 🐙 깃허브 — 검색 실패({str(e)[:60]})"]
        try:
            web = tools.google_search(q)
            lines += ["", "## 🔎 웹", web.strip()[:1200]]
        except Exception:
            pass
    lines += ["", "## 🔗 다른 저장소에서 통합한 것"]
    lines += [f"- {r}: {d}" for r, d in OTHER_REPOS.items()]
    return "\n".join(lines)


def _slug(name):
    return re.sub(r"[^a-z0-9-]+", "-", name.lower().replace("_", "-")).strip("-")[:64] or "skill"


def sync_claude():
    """회사 스킬·에이전트를 Claude Code 형식으로 묶어 이 저장소를 여는 모든 세션이 자동으로 쓰게 함."""
    sk_dir, ag_dir = ROOT / ".claude" / "skills", ROOT / ".claude" / "agents"
    sk_dir.mkdir(parents=True, exist_ok=True)
    ag_dir.mkdir(parents=True, exist_ok=True)
    made, keep_s, keep_a = [], set(), set()
    assets = local_assets()
    # 다른 저장소의 '규칙' 파일(브랜치·폴더 규칙 등)은 이 저장소 세션과 충돌할 수 있어 자동 스킬에서 빼고 검색으로만 씀
    for a in [x for x in assets if x["kind"] in ("스킬", "프롬프트") and not x["name"].endswith("-rules")]:
        name = _slug(a["name"])
        keep_s.add(name)
        body = re.sub(r"^\s*(?:<!--.*?-->\s*)*---\n.*?\n---\n", "", a["text"], count=1, flags=re.S)
        src = re.search(r"<!--\s*(source:[^>]*)-->", a["text"])
        lic = re.search(r"<!--\s*(license:[^>]*)-->", a["text"])
        desc = a["desc"].replace("\n", " ").replace('"', "'")[:900] or f"회사 {a['kind']} {a['name']}"
        if a["path"].count("/") > 1:  # prompts/<저장소>/… = 다른 저장소에서 통합한 참고 프롬프트
            desc = f"[참고 프롬프트 · {a['path'].split('/')[1]}] {desc} — 필요할 때 복사해서 쓰는 문안(이 저장소 작업 규칙보다 우선하지 않음)"
        d = sk_dir / name
        d.mkdir(exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: \"{desc}\"\n---\n<!-- 자동 생성: {a['path']} 에서 (mother hub sync) -->\n"
            + (f"<!-- {src.group(1).strip()} -->\n" if src else "") + (f"<!-- {lic.group(1).strip()} -->\n" if lic else "")
            + body.strip() + "\n", encoding="utf-8")
        made.append(f".claude/skills/{name}")
    for f in sorted((ROOT / "agents").glob("*.yaml")):
        s = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        name = _slug(f.stem)
        keep_a.add(name)
        desc = f"{s.get('title', f.stem)} 팀. {str(s.get('system', '')).splitlines()[0][:200] if s.get('system') else ''}".replace('"', "'")
        skills = ", ".join(s.get("skills", [])) or "없음"
        (ag_dir / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: \"{desc}\"\n---\n<!-- 자동 생성: agents/{f.name} 에서 (mother hub sync) -->\n"
            f"{s.get('system', '')}\n\n장착 스킬: {skills} (.claude/skills/ 에 있음)\n", encoding="utf-8")
        made.append(f".claude/agents/{name}.md")
    for d in sk_dir.iterdir():  # 원본이 사라진 자동 생성본 정리
        if d.is_dir() and d.name not in keep_s and (d / "SKILL.md").exists() and "자동 생성" in (d / "SKILL.md").read_text(encoding="utf-8")[:400]:
            (d / "SKILL.md").unlink()
            d.rmdir()
    for f in ag_dir.glob("*.md"):
        if f.stem not in keep_a and "자동 생성" in f.read_text(encoding="utf-8")[:400]:
            f.unlink()
    idx = ["# 회사 스킬·프롬프트·에이전트 목록 (자동 생성)", "", "통합 검색: `python -m mother search all \"할 일\"` · 앱 → 더보기 → 🔎 통합 검색", ""]
    for kind in ("스킬", "프롬프트", "에이전트"):
        idx.append(f"## {kind}")
        idx += [f"- **{a['name']}** — {a['desc'][:140]} (`{a['path']}`)" for a in assets if a["kind"] == kind] or ["- 없음"]
        idx.append("")
    (store.SKILLS / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")
    return f"🔗 통합 완료: 스킬·프롬프트 {len(keep_s)}개, 에이전트 {len(keep_a)}개 → .claude/ (모든 세션 자동 사용) · 목록 skills/INDEX.md"
