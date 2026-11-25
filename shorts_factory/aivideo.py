"""첫 장면(훅)용 AI 영상: Higgsfield API · Wan 3.0 (9:16, 무음, 5초). 키·예산 없으면 None → 이미지/실사로 대체.
키: HF_API_KEY_ID + HF_API_KEY_SECRET (console.higgsfield.ai). 웹 구독 크레딧과 별개인 API 잔액(최소 $5 충전)에서 차감.
"""
import json, os, time, urllib.request
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


def hook_clip(subject, out_dir: Path, seconds=5):
    """예산 안에서만 생성. 반환: mp4 경로 또는 None."""
    if os.environ.get("AI_VIDEO", "0") != "1" or not _auth():
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
    rows = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    rows.append({"date": date.today().isoformat(), "usd": usd, "model": MODEL, "subject": subject[:80]})
    LOG.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  🎬 AI 훅 영상 생성 (${usd:.2f}, 이번 달 ${month_spent():.2f}/${budget})")
    return out
