"""(jarvis 프로젝트에서 가져옴) 숏츠 훅·제목 채점 — LLM 없이 0토큰.

yt-script hookscore.py · yt-package title.py의 채점 기준을 한국어로 옮긴 것. 표준 라이브러리만 쓴다.

원본 스킬은 영어 정규식이라 한국어 문장은 엉뚱한 점수를 낸다(같은 제목·썸네일도 '다른 단어'로 본다).
점수 구조(속성 5개, 평균 60% + 최저점 40%, 제목은 100에서 문제당 -14 / 장점당 +4)는 원본 그대로다.
원본처럼 낮은 점수는 다시 볼 이유일 뿐, 높은 점수가 조회수를 약속하지 않는다.
"""
import json
import re
from pathlib import Path

HOOKS_FILE = Path(__file__).resolve().parent.parent / "skills" / "hooks.json"

CONCRETE = re.compile(r"\d[\d,.]*\s?(%|배|원|만|천|억|초|분|시간|일|주|개월|달|년|가지|개|번|명|장|kg|g|ml|도)?|(한|두|세|네|다섯)\s?(가지|번|배|개)")
VAGUE = re.compile(r"대박|미친|역대급|충격|최고의?|완벽|끝판왕|레전드|엄청난|놀라운|비밀|궁극|혁명")
FILLER = re.compile(r"^(사실|그냥|진짜|정말|너무|약간|좀|안녕하세요|오늘은?|이번엔?|영상|구독|채널|자|음|그)$")
YOU = re.compile(r"당신|여러분|(?<![가-힣])너(?![가-힣])|시나요|세요|셨나요|하시죠|나요\?")
STAKE = re.compile(r"손해|잃|날리|버리|낭비|망치|망가|후회|실수|위험|비용|돈|그만|절대|안 ?하면|모르면|전에|멈추|죽")
CURIOSITY = re.compile(r"왜|어떻게|무엇|뭐|어떤|이유|아무도|거의|빼고|하지만|그런데|사실은|알고 보니|딱")
CLOSED = re.compile(r"때문에|그래서|즉,")
TITLE_FILLER = {"이", "그", "저", "진짜", "정말", "오늘", "이번", "요즘", "그냥", "드디어"}
FIX = {
    "구체성": "형용사 하나를 숫자·이름·날짜로 바꾸기",
    "말 걸기": "첫 여섯 어절 안에 시청자에게 직접 말하기(여러분, ~하시나요)",
    "손해": "지금 방식을 계속하면 무엇을 잃는지 말하기",
    "궁금증": "스스로 답해 버리는 뒷부분을 잘라 내기",
    "길이": "6~18어절. 소리 내 읽다 숨이 찰 때 멈추기",
}


def _clip(value):
    return max(0, min(100, value))


def _brevity(text):
    n = len(text.split())
    if not n:
        return 0
    if 6 <= n <= 18:  # 영어 9~24단어(10초 낭독)에 해당하는 한국어 어절 범위
        return 100
    return max(30, 100 - (6 - n) * 14) if n < 6 else max(10, 100 - (n - 18) * 7)


def hook_score(text):
    t = (text or "").strip()
    if not t:
        return None
    tokens = t.split()
    parts = {
        "구체성": _clip(34 + 22 * len(CONCRETE.findall(t)) - 16 * len(VAGUE.findall(t)) - 5 * sum(bool(FILLER.match(w)) for w in tokens)
                     + min(18, 6 * len(re.findall(r"'[^']+'|\"[^\"]+\"|[A-Z][a-zA-Z]+", t)))),
        "말 걸기": _clip(26 + 20 * len(YOU.findall(t)) + (30 if YOU.search(" ".join(tokens[:6])) else 0)),
        "손해": _clip(22 + 26 * len(STAKE.findall(t)) + (14 if CONCRETE.search(t) else 0)),
        "궁금증": _clip(24 + 17 * len(CURIOSITY.findall(t)) + (18 if t.endswith("?") else 0) - (18 if CLOSED.search(t) else 0)),
        "길이": _brevity(t),
    }
    values = list(parts.values())
    verdict = round(0.6 * sum(values) / len(values) + 0.4 * min(values))
    weakest = min(parts, key=parts.get)
    return {"text": t, "parts": parts, "verdict": verdict, "band": "강함" if verdict >= 72 else "쓸 만함" if verdict >= 55 else "약함",
            "weakest": weakest, "fix": FIX[weakest]}


def _bigrams(text):
    s = re.sub(r"[^0-9a-zA-Z가-힣]", "", text.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def title_check(title, thumb=None):
    t = (title or "").strip()
    n, issues, good = len(t), [], []
    if n > 100:
        issues.append(f"{n}자: 유튜브 제목 한도 100자 초과")
    elif n > 60:
        issues.append(f"{n}자: 데스크톱 검색에서 60자 근처가 잘림")
    else:
        good.append(f"{n}자, 데스크톱 60자 안")
    if n > 40:
        issues.append(f"모바일 피드에는 '{t[:40]}…'까지만 보임. 핵심이 앞에 있는지 확인")
    if t.count("!") > 2:
        issues.append("느낌표가 3개 이상이라 광고처럼 읽힘")
    vague = sorted(set(VAGUE.findall(t)))
    if vague:
        issues.append(f"막연한 말({', '.join(vague)}) → 숫자·이름·날짜로 바꾸기")
    nums = re.findall(r"\d[\d,.]*%?", t)
    if nums:
        good.append(f"구체적인 숫자 포함({', '.join(nums[:3])})")
    else:
        issues.append("숫자·날짜·이름이 없음. 가장 확실한 한 가지 개선")
    if t.endswith("?"):
        good.append("질문으로 끝나 궁금증을 남김")
    head = re.sub(r"[^\w가-힣 ]", "", t).split()[:2]
    if head and all(w in TITLE_FILLER for w in head):
        issues.append("앞 두 어절이 군말. 주제를 앞으로")
    if thumb:
        a, b = _bigrams(t), _bigrams(thumb)
        overlap = len(a & b) / max(1, min(len(a), len(b)))
        if overlap >= 0.5:
            issues.append(f"썸네일 글자가 제목과 {round(overlap * 100)}% 겹침. 썸네일은 제목이 말하지 않는 것을 말해야 함")
        else:
            good.append("썸네일과 제목이 서로 다른 말을 함")
        if len(thumb.split()) > 4:
            issues.append(f"썸네일 글자 {len(thumb.split())}어절. 피드 크기에서는 3어절이 한계")
    return {"title": t, "chars": n, "score": _clip(100 - 14 * len(issues) + 4 * len(good)), "issues": issues, "good": good}


def hook_formulas():
    """후킹 공식 21개(이름·형태·예시·실패 조건). 스킬이 없으면 빈 목록."""
    try:
        hooks = json.loads(HOOKS_FILE.read_text(encoding="utf-8"))["hooks"]
    except (OSError, ValueError, KeyError):
        return []
    return [{k: h.get(k, "") for k in ("id", "name", "shape", "example", "fails_when")} for h in hooks]
