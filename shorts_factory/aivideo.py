"""첫 장면(훅)용 AI 영상 (9:16, 무음). 키·예산 없으면 None → 이미지/실사로 대체.
- gemini (기본): Gemini 영상 모델 — GEMINI_API_KEY, AI Studio 결제 연결 필요. (jarvis/geminivideo.py 방식 계승)
- higgsfield (선택): HF_API_KEY_ID + HF_API_KEY_SECRET, API 잔액에서 차감.
AI_VIDEO_PROVIDER 로 선택.
"""
import base64, json, os, time, urllib.error, urllib.request
from datetime import date
from pathlib import Path

BASE = "https://api.higgsfield.ai"
MODEL = "alibaba/wan-3.0/text-to-video"
LOG = Path(__file__).resolve().parent / "aivideo_log.json"
STYLE = ("vertical 9:16 cinematic shot, photorealistic, dynamic camera push-in, single clear subject, "
         "dramatic natural light, no text, no letters, no watermark")


def _auth():
    kid, sec = os.environ.get("HF_API_KEY_ID"), os.environ.get("HF_API_KEY_SECRET")
    if kid and sec:
        return f"Key {kid}:{sec}"
    if os.environ.get("HF_KEY"):
        return f"Key {os.environ['HF_KEY']}"
    return None


def _call(method, url, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                               headers={"Authorization": _auth(), "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.load(f)


def month_spent():
    rows = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    m = date.today().isoformat()[:7]
    return sum(float(r.get("usd", 0)) for r in rows if r["date"][:7] == m)


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_MODEL = os.environ.get("GEMINI_VIDEO_MODEL", "gemini-omni-1.2-flash")
GEMINI_USD_PER_SEC = 0.07  # 720p 기준(2026-11-16 확인값, jarvis/geminivideo.py)


def _log(usd, model, subject):
    rows = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    rows.append({"date": date.today().isoformat(), "usd": usd, "model": model, "subject": subject[:80]})
    LOG.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def gemini_clip(subject, out_dir: Path, seconds=4):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    budget = float(os.environ.get("AI_VIDEO_BUDGET", "5"))
    usd = round(seconds * GEMINI_USD_PER_SEC, 2)
    if month_spent() + usd > budget:
        print(f"  💸 이번 달 AI 영상 예산 ${budget} 초과 예정 → 건너뜀")
        return None
    body = {"model": GEMINI_MODEL, "input": f"{subject}. {STYLE}",
            "response_format": {"type": "video", "aspect_ratio": "9:16", "resolution": "720p", "duration": f"{seconds}s"}}
    req = urllib.request.Request(GEMINI_API, json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            reply = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ Gemini 영상 불가({e.code}) — AI Studio 결제 연결이 필요할 수 있어요")
        return None
    video = None
    for step in reply.get("steps", []):
        if step.get("type") == "model_output":
            video = next((c for c in step.get("content", []) if c.get("type") == "video" and c.get("data")), None) or video
    if not video:
        print("  ⚠️ Gemini 영상이 오지 않음(안전 필터 등)")
        return None
    out = out_dir / "ai_hook.mp4"
    out.write_bytes(base64.b64decode(video["data"]))
    _log(usd, GEMINI_MODEL, subject)
    print(f"  🎬 AI 훅 영상(Gemini) ${usd}, 이번 달 ${month_spent():.2f}/${budget}")
    return out


def hook_clip(subject, out_dir: Path, seconds=5):
    """예산 안에서만 생성. 반환: mp4 경로 또는 None."""
    if os.environ.get("AI_VIDEO", "0") != "1":
        return None
    if os.environ.get("AI_VIDEO_PROVIDER", "gemini") == "gemini":
        return gemini_clip(subject, out_dir)
    if not _auth():
        return None
    budget = float(os.environ.get("AI_VIDEO_BUDGET", "5"))
    body = {"prompt": f"{subject}. {STYLE}", "duration": seconds, "resolution": "720p",
            "aspect_ratio": "9:16", "generate_audio": False}
    try:
        usd = float(_call("POST", f"{BASE}/estimate/{MODEL}", body).get("usd", 0))
    except Exception:
        usd = 0.5  # 견적 실패 시 보수적으로 계산
    if month_spent() + usd > budget:
        print(f"  💸 이번 달 AI 영상 예산 ${budget} 초과 예정 → 건너뜀")
        return None
    sub = _call("POST", f"{BASE}/{MODEL}", body)
    status_url = sub.get("status_url") or f"{BASE}/requests/{sub['request_id']}/status"
    for _ in range(72):  # 최대 6분 대기
        s = _call("GET", status_url)
        if s.get("status") in ("completed", "failed", "nsfw", "canceled"):
            break
        time.sleep(5)
    url = (s.get("video") or {}).get("url")
    if s.get("status") != "completed" or not url:
        print(f"  ⚠️ AI 영상 실패({s.get('status')})")
        return None
    out = out_dir / "ai_hook.mp4"
    urllib.request.urlretrieve(url, out)
    _log(usd, MODEL, subject)
    print(f"  🎬 AI 훅 영상 생성 (${usd:.2f}, 이번 달 ${month_spent():.2f}/${budget})")
    return out


# ───────────────── Gemini Veo: 사진 → 움직이는 영상 (Gemini API, AI Studio 결제 연결 필요) ─────────────────
VEO_USD_PER_SEC = float(os.environ.get("VEO_USD_PER_SEC", "0.15"))  # 빠른 모델 기준 보수적 추정 — 실제 요금은 AI Studio 청구서 기준
_veo = {"model": None, "down": False}


def _veo_model(key):
    if _veo["model"] is None:
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            ms = [m["name"] for m in json.load(r).get("models", [])
                  if "veo" in m["name"].lower() and "predictLongRunning" in m.get("supportedGenerationMethods", [])]
        ms.sort(key=lambda n: ("fast" not in n, "preview" in n, n))  # 빠르고 싼 안정판 먼저
        _veo["model"] = ms[0] if ms else ""
    return _veo["model"]


def veo_animate(img, prompt, out: Path, seconds=8):
    """장면 사진(인물 참조 포함)을 Veo로 움직이는 영상으로. 예산·결제·한도 안 되면 None → 무료 영상 AI/사진 줌으로."""
    key = os.environ.get("GEMINI_API_KEY")
    if _veo["down"] or not key or os.environ.get("GEMINI_VIDEO", "1") != "1":
        return None
    out = Path(out)
    if out.exists():
        return out
    budget = float(os.environ.get("AI_VIDEO_BUDGET", "5"))
    usd = round(seconds * VEO_USD_PER_SEC, 2)
    if month_spent() + usd > budget:
        print(f"  💸 이번 달 Gemini 영상 예산 ${budget} 다 씀 → 무료 영상 AI로", flush=True)
        _veo["down"] = True
        return None
    try:
        model = _veo_model(key)
        if not model:
            raise RuntimeError("Veo 모델이 이 키에 안 보임")
        data = Path(img).read_bytes()
        mime = "image/jpeg" if str(img).lower().endswith((".jpg", ".jpeg")) else "image/png"
        body = {"instances": [{"prompt": prompt[:1500], "image": {"bytesBase64Encoded": base64.b64encode(data).decode(), "mimeType": mime}}],
                "parameters": {"aspectRatio": "9:16", "personGeneration": "allow_adult",
                               "negativePrompt": "text, subtitles, watermark, distorted face, extra fingers"}}
        hdr = {"Content-Type": "application/json", "x-goog-api-key": key}
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/{model}:predictLongRunning",
                                         json.dumps(body).encode(), headers=hdr, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                op = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 400:
                raise
            body["parameters"].pop("personGeneration", None)  # 일부 모델·지역은 이 옵션을 안 받음
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/{model}:predictLongRunning",
                                         json.dumps(body).encode(), headers=hdr, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                op = json.load(r)
        for _ in range(60):  # 최대 약 10분
            time.sleep(10)
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/{op['name']}", headers={"x-goog-api-key": key}), timeout=30) as r:
                op = json.load(r)
            if op.get("done"):
                break
        if op.get("error") or not op.get("done"):
            raise RuntimeError(str(op.get("error") or "시간 초과")[:120])
        res = op.get("response", {})
        samples = (res.get("generateVideoResponse") or res).get("generatedSamples") or res.get("videos") or []
        uri = (samples[0].get("video") or {}).get("uri") if samples else None
        if not uri:
            raise RuntimeError("영상이 오지 않음(안전 필터 등)")
        with urllib.request.urlopen(urllib.request.Request(uri, headers={"x-goog-api-key": key}), timeout=120) as r:
            out.write_bytes(r.read())
        _log(usd, model.split("/")[-1], prompt)
        print(f"  🎬 Gemini Veo 영상 {out.name} (${usd}, 이번 달 ${month_spent():.2f}/${budget})", flush=True)
        return out
    except Exception as e:
        _veo["down"] = True  # 이번 실행에서는 더 부르지 않음
        code = getattr(e, "code", "")
        why = "AI Studio 결제 연결이 필요해요" if code in (429, 403, 400) else str(e)[:80]
        print(f"  ⚠️ Gemini Veo 불가({code or 'x'}) — {why} → 무료 영상 AI로", flush=True)
        return None
