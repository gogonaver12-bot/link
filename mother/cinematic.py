"""시네마틱 프롬프트 5단계 황금 공식 (사장님 지정, 2026-11-28).
[1 샷 크기·카메라 무빙] + [2 피사체·구체적 동작 1개] + [3 배경·질감] + [4 조명·색감] + [5 카메라·렌즈 스펙] 순서로 영문 작성.
금지: 추상 형용사(beautiful·masterpiece·ultra 8k…), 한 클립에 동작 여러 개, 카메라 무빙 없는 고정 화면.
"""
import re

WRITER_RULE = (
    "shot 은 영어로, 아래 5요소를 이 순서대로 한 문단에: "
    "① 샷 크기+카메라 무빙(예: Medium close-up, slow dolly in / Low-angle tracking shot / Handheld camera) "
    "② 피사체 [id] + 동작 딱 1개를 동사로 구체적으로(예: turning head slowly, beads of sweat dripping, fabric fluttering in the wind) "
    "③ 배경 깊이와 표면 질감(예: wet asphalt reflecting neon lights, dust particles floating in the air, weathered concrete) "
    "④ 빛의 방향·시간대·색보정(예: golden hour backlighting, volumetric god rays, chiaroscuro lighting, teal and orange color grading). "
    "렌즈 스펙은 자동으로 붙으니 쓰지 말 것. beautiful·awesome·masterpiece·ultra 8k 같은 추상 형용사 금지, 한 장면에 동작 2개 이상 금지."
)

_ABSTRACT = r"\b(beautiful|awesome|stunning|epic|amazing|masterpiece|best quality|ultra[- ]?detailed|highly detailed|ultra[- ]?8k|8k|ultra hd)\b,?\s*"
_MOVES = ("dolly", "push in", "push-in", "pull out", "pull-out", "tracking", "pan ", "panning", "tilt", "orbit", "crane", "handheld",
          "drone", "fpv", "zoom", "follow", "arc shot", "steadicam")
_SIZES = ("extreme close-up", "close-up", "close up", "medium", "wide", "full shot", "aerial", "over-the-shoulder", "two shot", "macro",
          "establishing", "low-angle", "high-angle", "pov")


def clean(text):
    """추상 형용사 제거(오히려 과장된 CG 느낌을 냄) + 공백 정리."""
    t = re.sub(_ABSTRACT, "", text or "", flags=re.I)
    return re.sub(r"\s{2,}", " ", re.sub(r"\s+([,.])", r"\1", t)).strip(" ,.")


def lens(text):
    """⑤ 카메라·렌즈 스펙: 샷 종류에 맞는 실제 시네마 카메라·렌즈."""
    t = (text or "").lower()
    if any(k in t for k in ("macro", "product", "detail of")):
        return "Shot on Phantom Flex4K, 100mm macro lens, razor-sharp focus, warm rim lighting, natural film grain"
    if any(k in t for k in ("aerial", "drone", "fpv", "establishing", "landscape")):
        return "Shot on DJI Inspire 3, 24mm lens, photorealistic, high dynamic range, natural film grain"
    if any(k in t for k in ("tracking", "running", "chase", "fight", "action", "handheld")):
        return "Shot on RED V-Raptor, 24mm wide-angle lens, high shutter speed, natural motion blur, cinematic contrast"
    if any(k in t for k in ("close-up", "close up", "closeup", "face", "eyes")):
        return ("Shot on ARRI Alexa 65, 85mm prime lens, f/1.4 shallow depth of field, hyper-realistic skin texture, "
                "natural 35mm film grain")
    return "Shot on ARRI Alexa 65, 35mm anamorphic lens, shallow depth of field, hyper-realistic skin texture, natural film grain"


def compose(shot, setting="", default_size="Medium shot"):
    """AI가 쓴 장면 묘사를 5단계 공식 순서로 정리: 샷·무빙이 없으면 맨 앞에 보충, 렌즈 스펙은 맨 끝에."""
    s = clean(shot)
    low = s.lower()
    head = []
    if not any(k in low for k in _SIZES):
        head.append(default_size)
    if not any(k in low for k in _MOVES):
        head.append("slow push in" if "close" in low or not head else "subtle handheld movement")
    lead = (", ".join(head) + ". ") if head else ""
    env = f" Setting: {clean(setting)}." if setting else ""  # ③ 배경은 렌즈 스펙 앞에
    return f"{lead}{s}.{env} {lens(s)}"
