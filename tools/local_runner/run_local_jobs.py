"""PC 렌더러: 앱/클라우드가 jarvis/local_jobs.json 에 넣은 쇼츠(호러 3D·AI 뉴스)를 이 PC에서 렌더해 폰 앱으로 보냄.
JARVIS-VIDEO-FACTORY(feat/video-unified) 작업 폴더의 Supertonic TTS·폰트·ffmpeg 를 그대로 씀. 비밀키 없음.
처음 실행 때 local_config.json(이 PC 전용, 저장소에 안 올라감)을 만들어 경로를 물어봄.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINK = HERE.parents[1]
CFG = HERE / "local_config.json"
DEFAULT = {
    "factory_dir": r"C:\Users\gogo8\Documents\Codex\2026-11-04\referenced-chatgpt-conversation-this-is-an\work",
    "assets": "assets", "ko_model": "models/supertonic-3", "tts_python": r".venv-ko-tts\Scripts\python.exe",
    "python": "python", "bitrate": "4.5M", "glitch": False,
}
MODULE = {"horror": "jarvis.shorts_horror3d", "ainews": "jarvis.shorts_ainews"}


def config():
    if CFG.exists():
        return {**DEFAULT, **json.loads(CFG.read_text(encoding="utf-8"))}
    c = dict(DEFAULT)
    print("처음 한 번만: 영상 공장 작업 폴더 경로를 확인할게요 (엔터 = 기본값)")
    for k in ("factory_dir", "assets", "ko_model", "tts_python"):
        v = input(f"  {k} [{c[k]}]: ").strip()
        c[k] = v or c[k]
    CFG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    return c


def git(*a):
    return subprocess.run(["git", "-C", str(LINK), *a], capture_output=True, text=True)


def finish(mp4, c):
    """폰 전송 한도(30MB) 안으로: 비트레이트 제한 + (선택) 장면 전환 글리치."""
    out = mp4.with_name(mp4.stem + "-phone.mp4")
    vf = ["scale=720:-2"]
    if c.get("glitch"):
        vf.append("rgbashift=rh=-6:bh=6:enable='lt(mod(t\\,4)\\,0.12)'")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", ",".join(vf), "-c:v", "libx264", "-b:v", c["bitrate"],
                    "-maxrate", c["bitrate"], "-bufsize", "9M", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)], check=True)
    return out


def main():
    c = config()
    fd = Path(c["factory_dir"])
    git("pull", "-q", "--rebase", "origin", "main")
    jf = LINK / "jarvis" / "local_jobs.json"
    jobs = json.loads(jf.read_text(encoding="utf-8")) if jf.exists() else []
    todo = [j for j in jobs if j.get("status") == "pending"]
    if not todo:
        print("✅ 대기 중인 PC 렌더 없음")
        return
    prev = LINK / "app" / "previews"
    prev.mkdir(parents=True, exist_ok=True)
    for j in todo:
        out_dir = fd / "out" / j["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [c["python"], "-m", MODULE[j["kind"]], "--assets", c["assets"], "--ko-model", c["ko_model"],
               "--tts-python", c["tts_python"], "--output", str(out_dir), "--plan", str(LINK / j["plan"])]
        if j.get("speed"):
            cmd += ["--speed", str(j["speed"])]
        print("🎬 렌더:", j["title"], flush=True)
        r = subprocess.run(cmd, cwd=fd, capture_output=True, text=True)
        mp4s = sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
        if r.returncode or not mp4s:
            j["status"], j["error"] = "failed", (r.stderr or r.stdout)[-600:]
            print("⚠️ 실패:", j["error"][-300:])
            continue
        phone = finish(mp4s[-1], c)
        dst = prev / f"local-{j['id']}.mp4"
        shutil.copy(phone, dst)
        j.update(status="done", done=datetime.now().isoformat(timespec="seconds"), file=f"app/previews/{dst.name}",
                 mb=round(dst.stat().st_size / 1e6, 1))
        idx_f = LINK / "data" / "previews.json"
        idx = json.loads(idx_f.read_text(encoding="utf-8")) if idx_f.exists() else []
        idx = [x for x in idx if x["file"] != dst.name] + [{"file": dst.name, "title": f"🖥 {j['title']}", "date": j["done"][:10]}]
        idx_f.write_text(json.dumps(idx[-6:], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ {dst.name} ({j['mb']}MB)")
    jf.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    git("add", "jarvis/local_jobs.json", "data/previews.json", "app/previews")
    git("commit", "-qm", "pc: 로컬 렌더 쇼츠 결과")
    r = git("push", "-q", "origin", "HEAD:main")
    print("📱 폰 앱 → 영상확인 → '방금 만든 영상'에서 보세요" if r.returncode == 0
          else f"⚠️ 업로드 실패 — 결과는 {prev} 에 있어요: {r.stderr.strip()[:200]}")


if __name__ == "__main__":
    sys.exit(main())
