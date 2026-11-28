"""배경음악·효과음: 유튜브 오디오 보관함 파일(암호화 보관) → 없으면 효과음은 ffmpeg로 합성.
audio.enc = audio_src/{music,sfx} 를 zip 후 AUDIO_KEY(Fernet)로 암호화한 파일. 공개 저장소라 원본은 올리지 않음.
"""
import io, os, random, zipfile
from pathlib import Path

ROOT = Path(__file__).parent
ENC = ROOT / "audio.enc"
DIR = ROOT / "audio"  # 복호화 위치 (.gitignore)
EXT = (".mp3", ".wav", ".m4a", ".ogg")
SFX_WORDS = {"whoosh": ("whoosh", "swoosh", "swish", "transition", "wind"),
             "pop": ("pop", "click", "tap", "bubble", "blip"),
             "ding": ("ding", "bell", "chime", "notification", "success")}
SYNTH = {  # 파일이 없을 때 쓰는 합성 효과음
    "whoosh": "anoisesrc=d=0.45:c=pink:a=0.6,highpass=f=400,lowpass=f=4000,afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.25",
    "pop": "sine=f=880:d=0.07,afade=t=out:d=0.07",
    "ding": "sine=f=1320:d=0.7,afade=t=out:st=0.05:d=0.65",
}


def unpack():
    key = os.getenv("AUDIO_KEY")
    if DIR.exists() or not (ENC.exists() and key):
        return
    from cryptography.fernet import Fernet, InvalidToken
    try:
        raw = Fernet(key.strip().encode()).decrypt(ENC.read_bytes())
    except (InvalidToken, ValueError):
        print("  ⚠️ AUDIO_KEY 가 audio.enc 와 맞지 않아요 — audio_pack.bat 다시 실행")
        return
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():  # 경로 탈출 방지: music/ sfx/ 바로 아래 파일만
            parts = Path(n).parts
            if len(parts) == 2 and parts[0] in ("music", "sfx") and n.lower().endswith(EXT):
                (DIR / parts[0]).mkdir(parents=True, exist_ok=True)
                (DIR / parts[0] / parts[1]).write_bytes(z.read(n))


def _files(kind):
    d = DIR / kind
    return sorted(p for p in d.iterdir() if p.suffix.lower() in EXT) if d.exists() else []


def music(seed=""):
    unpack()
    tracks = _files("music")
    return random.Random(seed).choice(tracks) if tracks else None


def sfx(kind, seed=""):
    """반환: ffmpeg 입력 인자 목록 (파일이면 ['-i', path], 합성이면 lavfi)."""
    unpack()
    hits = [p for p in _files("sfx") if any(w in p.name.lower() for w in SFX_WORDS[kind])]
    if hits:
        return ["-i", str(random.Random(seed + kind).choice(hits))]
    return ["-f", "lavfi", "-i", SYNTH[kind]]


def mix(cues, total, seed="", first_input=2, story=False):
    """음성(1번 입력) + 음악(덕킹) + 효과음. 반환: (추가 입력 인자, filter_complex 오디오 부분)."""
    args, n = [], first_input
    f = ["[1:a]asplit=2[vo][vk]"]
    mix_in = ["[vo]"]
    m = music(seed)
    if m:
        args += ["-stream_loop", "-1", "-i", str(m)]
        f.append(f"[{n}:a]volume={0.16 if story else 0.30}[m0];[m0][vk]sidechaincompress=threshold=0.04:ratio=8:attack=15:release=350[m]")
        mix_in.append("[m]"); n += 1
    else:
        f.append("[vk]anullsink")
    starts = [c[0] for c in cues[1:]][:12]  # 장면 바뀔 때마다 톡
    fx = () if story else (("whoosh", [0.0], 0.55), ("pop", starts, 0.30), ("ding", [max(total - 0.9, 0)], 0.35))
    for kind, times, vol in fx:  # 드라마는 효과음 없이(장면마다 '톡' 소리는 몰입을 깸) — 음악만 작게, 소리는 영상·목소리 그대로
        if not times:
            continue
        args += sfx(kind, seed)
        outs = "".join(f"[{kind}{i}]" for i in range(len(times)))
        f.append(f"[{n}:a]volume={vol},asplit={len(times)}{outs}" if len(times) > 1 else f"[{n}:a]volume={vol}[{kind}0]")
        for i, t in enumerate(times):
            ms = int(t * 1000)
            f.append(f"[{kind}{i}]adelay={ms}|{ms}[{kind}d{i}]")
            mix_in.append(f"[{kind}d{i}]")
        n += 1
    f.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:duration=first:normalize=0,alimiter=limit=0.95[a]")
    return args, ";".join(f)
