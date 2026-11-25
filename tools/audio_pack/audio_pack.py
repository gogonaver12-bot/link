"""PC에서 실행: 유튜브 오디오 보관함에서 받은 음악·효과음을 암호화해 저장소에 올림 (원본은 공개 안 됨).
1) C:\\link\\audio_src\\music 에 음악, audio_src\\sfx 에 효과음(mp3) 넣기  2) audio_pack.bat 더블클릭
키(AUDIO_KEY)는 GitHub Secrets 에만 저장. gh 로그인돼 있으면 자동, 아니면 값을 보여줌 → Secrets 에 붙여넣기.
"""
import io, os, shutil, subprocess, sys, zipfile
from pathlib import Path

from cryptography.fernet import Fernet

HERE = Path(__file__).resolve().parent
REPO_DIR = HERE.parents[1]
SRC = REPO_DIR / "audio_src"
OUT = REPO_DIR / "shorts_factory" / "audio.enc"
KEYF = HERE / ".audio_key"
REPO = "gogonaver12-bot/link"
EXT = (".mp3", ".wav", ".m4a", ".ogg")
LIMIT_MB = 90


def main():
    for d in ("music", "sfx"):
        (SRC / d).mkdir(parents=True, exist_ok=True)
    files = [p for d in ("music", "sfx") for p in sorted((SRC / d).iterdir()) if p.suffix.lower() in EXT]
    if not files:
        print(f"📂 {SRC} 의 music / sfx 폴더에 파일을 넣고 다시 실행하세요.")
        print("   유튜브 스튜디오 → 오디오 보관함 → '저작자 표시 필요 없음' 필터 → 다운로드")
        if os.name == "nt":
            os.startfile(SRC)
        return
    size = sum(p.stat().st_size for p in files) / 1e6
    if size > LIMIT_MB:
        sys.exit(f"❌ 총 {size:.0f}MB — {LIMIT_MB}MB 이하로 줄여주세요 (음악 10곡 정도 추천)")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for p in files:
            z.write(p, f"{p.parent.name}/{p.name}")
    new_key = not KEYF.exists()
    key = KEYF.read_bytes().strip() if not new_key else Fernet.generate_key()
    OUT.write_bytes(Fernet(key).encrypt(buf.getvalue()))
    print(f"🔒 음악 {len(list((SRC / 'music').iterdir()))}개 · 효과음 {len(list((SRC / 'sfx').iterdir()))}개 → 암호화 완료 ({size:.1f}MB)")

    gh = shutil.which("gh")
    saved = gh and subprocess.run([gh, "secret", "set", "AUDIO_KEY", "--repo", REPO], input=key.decode(),
                                  text=True, capture_output=True).returncode == 0
    if saved:
        KEYF.write_bytes(key)
        print("✅ AUDIO_KEY → GitHub Secrets 자동 저장")
    elif new_key:
        KEYF.write_bytes(key)
        print(f"\n👉 https://github.com/{REPO}/settings/secrets/actions/new 에서\n   이름: AUDIO_KEY\n   값:   {key.decode()}\n")
    git = lambda *a: subprocess.run(["git", "-C", str(REPO_DIR), *a], capture_output=True, text=True)
    git("pull", "-q", "--rebase", "origin", "main")
    git("add", str(OUT))
    git("commit", "-qm", "audio: 배경음악·효과음 갱신(암호화)")
    r = git("push", "-q", "origin", "HEAD:main")
    print("✅ 업로드 완료 — 다음 숏츠부터 배경음악·효과음 적용" if r.returncode == 0
          else f"⚠️ 업로드 실패: {r.stderr.strip()[:200]}\n   GitHub Desktop 등으로 shorts_factory/audio.enc 를 올려주세요")


if __name__ == "__main__":
    main()
