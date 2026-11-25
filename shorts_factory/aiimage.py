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


def generate(keyword, cache: Path, refs=None, style=None, name=None):
    """refs: 같은 인물로 그리기 위한 참조 이미지 경로들(캐릭터 시트). style: 기본 스타일 대신 쓸 문장."""
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    cache.mkdir(parents=True, exist_ok=True)
    prompt = f"{keyword}. {style or STYLE}"
    refs = [Path(r) for r in (refs or []) if Path(r).exists()]
    key = prompt + "|".join(r.name for r in refs)
    out = cache / (name or ("ai_" + hashlib.md5(key.encode()).hexdigest()[:12] + ".png"))
    if out.exists():
        return out
    m = model()
    if not m:
        raise RuntimeError("이미지 생성 모델 없음")
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
            raise RuntimeError(f"이미지 생성 실패 {e.code}") from e
    for part in (res.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
        data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
        if data:
            out.write_bytes(base64.b64decode(data))
            return out
    return None
