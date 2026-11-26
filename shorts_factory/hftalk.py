"""주인공이 실제로 말하는 영상 (무료, 입 모양 맞춤): 장면 사진 + 대사 목소리 → 말하며 움직이는 영상.
순서: Wan2.2-S2V(사진+목소리→말하는 영상) → LatentSync(움직이는 영상에 입 모양 맞추기) → EchoMimic(말하는 얼굴).
Hugging Face 공개 Space, HF_TOKEN 있으면 하루 사용량↑. 다 막히면 None → 말 없는 움직임 + 목소리.
"""
import os
import shutil
from pathlib import Path

_dead, _quota = set(), {"out": False}


def _try(space, ep, kw):
    import hfjob
    r = hfjob.predict(space, ep, kw, timeout=300)  # 대기 줄에서 5분 넘게 못 기다림
    v = r[0] if isinstance(r, (list, tuple)) else r
    return v["video"] if isinstance(v, dict) else v


def talk(img, audio, out: Path, motion=None):
    """img: 장면 사진, audio: 그 줄 대사 목소리(mp3/wav), motion: 같은 장면의 움직이는 영상(있으면 입 모양만 맞춤)."""
    if _quota["out"] or os.getenv("FREE_TALK", "1") != "1" or not audio:
        return None
    out = Path(out)
    if out.exists():
        return out
    try:
        from gradio_client import handle_file
    except ImportError:
        return None
    plans = [("Wan-AI/Wan2.2-S2V", "/predict", lambda: dict(ref_img=handle_file(str(img)), audio=handle_file(str(audio)), resolution="480P"))] if img else []
    if motion:
        plans.append(("fffiloni/LatentSync", "/generate_lip_sync_video",
                      lambda: dict(input_video_path=handle_file(str(motion)), input_audio_path=handle_file(str(audio)))))
    if img:
        plans.append(("fffiloni/EchoMimic", "/generate_video",
                      lambda: dict(uploaded_img=handle_file(str(img)), uploaded_audio=handle_file(str(audio)), width=512, height=768,
                                   length=1200, seed=420, facemask_dilation_ratio=0.1, facecrop_dilation_ratio=0.5, context_frames=12,
                                   context_overlap=3, cfg=2.5, steps=30, sample_rate=16000, fps=24, device="cuda")))
    for space, ep, kw in plans:
        if space in _dead:
            continue
        try:
            shutil.copy(_try(space, ep, kw()), out)
            print(f"  🗣️ 말하는 영상 ({space.split('/')[1]}) {out.name}", flush=True)
            return out
        except Exception as e:
            msg = str(e).lower()
            if "quota" in msg:
                print(f"  ⏳ 말하는 영상 AI 오늘 사용량 끝({space.split('/')[1]}) → 다음 AI", flush=True)
            elif "예산" in str(e) or isinstance(e, TimeoutError) or "timeout" in msg:
                print(f"  ⏱️ 말하는 영상 AI 너무 오래 걸림({space.split('/')[1]}) → 다음 AI", flush=True)
            _dead.add(space)
    _quota["out"] = True
    print("  ⚠️ 말하는 영상 AI 모두 막힘 → 나머지 대사는 움직이는 장면 + 목소리로 (HF_TOKEN 넣으면 사용량↑)", flush=True)
    return None
