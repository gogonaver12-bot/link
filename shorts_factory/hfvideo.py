"""사진 → 움직이는 영상 (무료): Hugging Face 공개 Space(Wan2.2 · LTX-Video · Wan2.1)를 차례로 시도.
HF_TOKEN(무료 계정 토큰)이 있으면 하루 GPU 사용량이 늘어나요. 사용량이 바닥나면 None → 사진 줌 효과로 대체.
"""
import os
import shutil
from pathlib import Path

NEG = "static, frozen, blurry, distorted face, deformed hands, extra fingers, text, subtitles, watermark, low quality"
_dead, _quota = set(), {"out": False}


def _spaces(img, prompt, sec):
    from gradio_client import handle_file
    return [
        ("zerogpu-aoti/wan2-2-fp8da-aoti-faster", "/generate_video",
         dict(input_image=handle_file(img), prompt=prompt, steps=6, negative_prompt=NEG, duration_seconds=min(sec, 5),
              guidance_scale=1, guidance_scale_2=1, seed=42, randomize_seed=False)),
        ("Lightricks/ltx-video-distilled", "/image_to_video",
         dict(prompt=prompt, negative_prompt=NEG, input_image_filepath=handle_file(img), input_video_filepath=None, height_ui=896,
              width_ui=512, mode="image-to-video", duration_ui=min(sec, 5), ui_frames_to_use=9, seed_ui=42, randomize_seed=False,
              ui_guidance_scale=1, improve_texture_flag=True)),
        ("multimodalart/wan2-1-fast", "/generate_video",
         dict(input_image=handle_file(img), prompt=prompt, height=896, width=512, negative_prompt=NEG, duration_seconds=min(sec, 3),
              guidance_scale=1.0, steps=4, seed=42, randomize_seed=False)),
    ]


def animate(img, prompt, out: Path, sec=3.5):
    """img(사진) 를 prompt 대로 움직이는 sec초 영상으로. 성공하면 out(mp4), 실패하면 None."""
    if _quota["out"] or os.getenv("FREE_VIDEO", "1") != "1":
        return None
    out = Path(out)
    if out.exists():
        return out
    try:
        from gradio_client import Client
    except ImportError:
        return None
    prompt = (prompt[:400] + ". Natural subtle motion: breathing, blinking, hair and clothes moving in the wind, "
              "slow cinematic camera push-in, consistent face, photorealistic")
    for space, ep, kw in _spaces(str(img), prompt, sec):
        if space in _dead:
            continue
        try:
            r = Client(space, token=os.getenv("HF_TOKEN") or None, verbose=False).predict(**kw, api_name=ep)
            v = r[0]["video"] if isinstance(r[0], dict) else r[0]
            shutil.copy(v, out)
            print(f"  🎞️ 사진→영상 ({space.split('/')[1]}) {out.name}", flush=True)
            return out
        except Exception as e:
            msg = str(e)
            if "quota" in msg.lower():
                print(f"  ⏳ 무료 영상 AI 오늘 사용량 끝({space.split('/')[1]}) → 다음 AI", flush=True)
            _dead.add(space)
    _quota["out"] = True
    print("  ⚠️ 무료 영상 AI 모두 사용량 끝 → 나머지 장면은 사진 줌 효과 (HF_TOKEN 넣으면 하루 사용량이 늘어요)", flush=True)
    return None
