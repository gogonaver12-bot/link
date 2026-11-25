#!/usr/bin/env python3
"""숏츠 공장: 대본 JSON -> 세로 1080x1920 최대 59초 MP4.

사용: python make_short.py scripts/001.json [--out out/]
배경: assets/clips/ 에 본인 소유/상업 라이선스 영상(mp4)을 넣으면 사용, 없으면 자동 그라데이션.
"""
import argparse, asyncio, json, subprocess, sys, random
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent
FONT = ROOT / "assets" / "BlackHanSans.ttf"
MAX_SEC = 59.0
W, H = 1080, 1920


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"명령 실패: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def dur(p):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(p)]).strip())


async def tts(text, voice, rate, path):
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def ass_time(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def wrap(text, n=11):
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > n and line:
            out.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    out.append(line)
    return r"\N".join(out)


def build_ass(cues, title, path):
    head = f"""[Script Info]
PlayResX: {W}
PlayResY: {H}
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Black Han Sans,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Hi,Black Han Sans,96,&H0000F0FF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Title,Black Han Sans,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC0000000,0,0,0,0,100,100,0,0,3,18,0,8,60,60,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    total = cues[-1][1] if cues else 1
    ev = [f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Title,,0,0,0,,{title.replace(chr(10), chr(92) + 'N') if chr(10) in title else wrap(title, 14)}"]
    for i, (s, e, txt) in enumerate(cues):
        style = "Hi" if i == 0 else "Sub"  # 첫 줄(훅) 노란색 강조
        pop = r"{\fscx80\fscy80\t(0,120,\fscx100\fscy100)}"
        ev.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},{style},,0,0,0,,{pop}{wrap(txt)}")
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


def background(total, colors, work, cues, keywords, subject=""):
    clips = sorted((ROOT / "assets" / "clips").glob("*.mp4"))
    if not clips and keywords:
        import stock
        print("🔎 무료 실사 영상 검색:", keywords)
        clips = stock.fetch(keywords, ROOT / "assets" / "stock_cache", want=len(keywords))
    try:  # 첫 장면(훅)은 AI 영상 (Higgsfield, 예산 안에서만)
        import aivideo
        hook = aivideo.hook_clip(subject or (keywords[0] if keywords else "mysterious cinematic scene"), work)
        if hook:
            clips = [hook] + list(clips)
    except Exception as e:
        print(f"  ⚠️ AI 훅 영상 건너뜀: {e}")
    bg = work / "bg.mp4"
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30"
    if not clips:
        c1, c2 = colors
        src = f"gradients=s={W}x{H}:c0={c1}:c1={c2}:x0=0:y0=0:x1={W}:y1={H}:speed=0.015:d={total:.2f},fps=30"
        sh(["ffmpeg", "-y", "-f", "lavfi", "-i", src, "-vf", "noise=alls=6:allf=t",
            "-c:v", "libx264", "-preset", "veryfast", bg])
        return bg
    # 자막 줄마다 컷 전환 + 천천히 줌인 (시선 유지)
    segs, bounds = [], [c[0] for c in cues[1:]] + [total]
    start = 0.0
    for i, end in enumerate(bounds):
        d = max(0.5, end - start)
        c = clips[i % len(clips)]
        seg = work / f"seg{i:02d}.mp4"
        frames = int(d * 30) + 1
        if c.suffix.lower() in (".jpg", ".jpeg", ".png"):  # 사진·AI 이미지: 켄번스 줌
            zp = f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},zoompan=z='1+0.0015*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s={W}x{H}:fps=30"
            sh(["ffmpeg", "-y", "-i", c, "-vf", f"{zp},eq=brightness=-0.08:saturation=1.15",
                "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", seg])
            segs.append(seg); start = end
            continue
        L = dur(c)  # 앞뒤 20%(제목/자막 카드 많음) 건너뜀
        off = random.uniform(L * 0.2, max(L * 0.2, L * 0.8 - d))
        zoom = f"zoompan=z='1.25+0.0012*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps=30"
        sh(["ffmpeg", "-y", "-ss", f"{off:.2f}", "-stream_loop", "-1", "-i", c, "-t", f"{d:.2f}",
            "-vf", f"{fit},{zoom},eq=brightness=-0.10:saturation=1.15", "-frames:v", str(frames),
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", seg])
        segs.append(seg); start = end
    lst = work / "segs.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs))
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", bg])
    return bg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", default=str(ROOT / "out"))
    a = ap.parse_args()
    sp = Path(a.script)
    s = json.loads(sp.read_text(encoding="utf-8"))
    voice = s.get("voice", "ko-KR-SunHiNeural")
    rate = s.get("rate", "+12%")
    lines = [s["hook"], *s["lines"], s.get("cta", "")]
    lines = [l for l in lines if l.strip()]

    work = Path(a.out) / f".work_{sp.stem}"
    work.mkdir(parents=True, exist_ok=True)
    cues, parts, t = [], [], 0.0
    for i, line in enumerate(lines):
        p = work / f"l{i:02d}.mp3"
        asyncio.run(tts(line, voice, rate, p))
        d = dur(p)
        if t + d > MAX_SEC:
            print(f"⚠️ 59초 초과 -> {i}번째 줄부터 잘림")
            break
        cues.append((t, t + d, line)); parts.append(p); t += d + 0.08

    lst = work / "a.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    voice_mp3 = work / "voice.m4a"
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-af", "apad=pad_dur=0.6,loudnorm=I=-14:TP=-1.5",
        "-c:a", "aac", "-b:a", "160k", voice_mp3])
    total = min(dur(voice_mp3), MAX_SEC)

    bg = background(total, s.get("colors", ["0x1a1a2e", "0xe94560"]), work, cues, s.get("keywords", []),
                    s.get("visual_hook", ""))
    ass = work / "sub.ass"
    build_ass(cues, s.get("cover") or s["title"], ass)

    out = Path(a.out) / f"{sp.stem}.mp4"
    music = ROOT / "assets" / "music.mp3"  # 선택: 저작권 프리 음악
    cmd = ["ffmpeg", "-y", "-i", bg, "-i", voice_mp3]
    afilter = "[1:a]anull[a]"
    if music.exists():
        cmd += ["-stream_loop", "-1", "-i", music]
        afilter = "[2:a]volume=0.12[m];[1:a][m]amix=inputs=2:duration=first[a]"
    cmd += ["-filter_complex", f"[0:v]ass={ass}:fontsdir={FONT.parent}[v];{afilter}",
            "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
    sh(cmd)
    meta = {"title": s["title"], "description": s.get("description", ""), "tags": s.get("tags", []),
            "duration": round(total, 1), "file": out.name}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {out} ({total:.1f}초)")


if __name__ == "__main__":
    main()
