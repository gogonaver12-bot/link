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


def generate(keyword, cache: Path):
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    cache.mkdir(parents=True, exist_ok=True)
    prompt = f"{keyword}. {STYLE}"
    out = cache / ("ai_" + hashlib.md5(prompt.encode()).hexdigest()[:12] + ".png")
    if out.exists():
        return out
    m = model()
    if not m:
        raise RuntimeError("이미지 생성 모델 없음")
    body = {"contents": [{"parts": [{"text": prompt}]}],
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
