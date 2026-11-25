"""장면별 AI 이미지 생성 (Gemini 이미지 모델, GEMINI_API_KEY). 실패하면 None → 무료 실사 영상으로 대체."""
import base64, hashlib, json, os, urllib.request
from pathlib import Path

BASE = "https://generativelanguage.googleapis.com/v1beta"
STYLE = ("vertical 9:16 photorealistic cinematic shot, natural light, shallow depth of field, rich color, "
         "single clear subject, room for captions at bottom, no text, no letters, no watermark, no logo")
_model = None


def _req(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                         "x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")})
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.load(f)


def model():
    """사용 가능한 이미지 생성 모델을 목록에서 자동 선택 (이름에 image, generateContent 지원)."""
    global _model
    if _model is None:
        names = []
        for m in _req(f"{BASE}/models?pageSize=200").get("models", []):
            if "image" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", []) and "tts" not in m["name"]:
                names.append(m["name"])
        names.sort(key=lambda n: ("preview" in n, n))  # 안정판 우선
        _model = names[0] if names else ""
    return _model


_gemini_down = False  # 이번 실행에서 Gemini 가 막혔으면(무료 한도 429 등) 다시 부르지 않음


def gemini(prompt, refs, out):
    global _gemini_down
    if _gemini_down or not os.environ.get("GEMINI_API_KEY"):
        return None
    try:
        m = model()
    except Exception:
        _gemini_down = True
        return None
    if not m:
        return None
    parts = [{"inline_data": {"mime_type": "image/jpeg" if r.suffix.lower() in (".jpg", ".jpeg") else "image/png",
                                "data": base64.b64encode(r.read_bytes()).decode()}} for r in refs[:3]]
    if parts:
        prompt = "Keep the exact same person(s) as in the reference image(s): same face, hair, outfit. " + prompt
    body = {"contents": [{"parts": parts + [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}
    try:
        res = _req(f"{BASE}/{m}:generateContent", body)
    except urllib.error.HTTPError as e:
        if e.code == 400:  # imageConfig 미지원 모델 → 기본 설정으로 재시도
            body["generationConfig"] = {"responseModalities": ["IMAGE", "TEXT"]}
            res = _req(f"{BASE}/{m}:generateContent", body)
        else:
            _gemini_down = True
            print(f"  ⚠️ Gemini 이미지 불가({e.code}) → 무료 이미지 AI(Pollinations)로")
            return None
    for part in (res.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
        data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
        if data:
            out.write_bytes(base64.b64decode(data))
            return out
    return None


def pollinations(prompt, out, seed=0, w=1080, h=1920):
    """무료 이미지 AI (FLUX, 키 없이 사용). POLLINATIONS_TOKEN 이 있으면 로고 없이·더 빠르게."""
    import time, urllib.parse
    q = urllib.parse.urlencode({"width": w, "height": h, "seed": seed, "model": "flux", "nologo": "true", "private": "true",
                                "enhance": "false"})
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:900])}?{q}"
    tok = os.environ.get("POLLINATIONS_TOKEN")
    for k in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": "link-shorts/1.0", **({"Authorization": f"Bearer {tok}"} if tok else {})})
            with urllib.request.urlopen(r, timeout=150) as f:
                data = f.read()
            if data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG":
                out.write_bytes(data)
                return out
        except urllib.error.HTTPError as e:
            if e.code != 429:
                return None
        except Exception:
            pass
        time.sleep(16 * (k + 1))  # 무료 등급은 15초에 1장 — 기다렸다 재시도
    return None


def generate(keyword, cache: Path, refs=None, style=None, name=None, seed=None):
    """refs: 같은 인물로 그리기 위한 참조 이미지(캐릭터 시트). 순서: Gemini(참조 사진으로 같은 얼굴) → Pollinations(무료, 같은 seed)."""
    cache.mkdir(parents=True, exist_ok=True)
    prompt = f"{keyword}. {style or STYLE}"
    refs = [Path(r) for r in (refs or []) if Path(r).exists()]
    key = prompt + "|".join(r.name for r in refs)
    out = cache / (name or ("ai_" + hashlib.md5(key.encode()).hexdigest()[:12] + ".png"))
    if out.exists():
        return out
    if gemini(prompt, refs, out):
        return out
    if os.environ.get("FREE_IMAGES", "1") == "1":
        jpg = out.with_suffix(".jpg")
        return pollinations(prompt, jpg, seed if seed is not None else int(hashlib.md5(key.encode()).hexdigest()[:6], 16))
    return None
