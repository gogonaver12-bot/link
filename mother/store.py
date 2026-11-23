"""파일 기반 저장소 (DB 없이 깃허브에 그대로 커밋되어 어디서든 이어서 사용)."""
import datetime as dt
import json
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AGENTS = ROOT / "agents"
SKILLS = ROOT / "skills"
REPORTS = ROOT / "reports"
WORKSPACE = ROOT / "workspace"
for _d in (DATA, AGENTS, SKILLS, REPORTS, WORKSPACE):
    _d.mkdir(exist_ok=True)

_cfg = None


def cfg():
    global _cfg
    if _cfg is None:
        _cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    return _cfg


def now():
    return dt.datetime.now(dt.timezone.utc)


def today():
    return now().date().isoformat()


def load_json(name, default):
    p = DATA / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(name, row):
    with (DATA / name).open("a", encoding="utf-8") as f:
        f.write(redact(json.dumps(row, ensure_ascii=False)) + "\n")


def read_jsonl(name):
    p = DATA / name
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def spend_on(day=None):
    day = day or today()
    return round(sum(r["usd"] for r in read_jsonl("usage.jsonl") if r["ts"][:10] == day), 4)


SECRET_PATTERNS = [r"Bearer\s+[^\s'\"]+(?:\s+[A-Za-z0-9._\-]{8,})?", r"AIza[0-9A-Za-z_\-]{20,}", r"AQ\.[A-Za-z0-9_.\-]{6,}",
                   r"sk-[A-Za-z0-9_\-]{16,}", r"gsk_[A-Za-z0-9]{16,}", r"github_pat_[A-Za-z0-9_]{16,}", r"ghp_[A-Za-z0-9]{16,}",
                   r"csk-[A-Za-z0-9]{16,}", r"ya29\.[A-Za-z0-9_.\-]{10,}", r"1//[A-Za-z0-9_\-]{20,}"]


def redact(text):
    """기록·화면에 키가 절대 남지 않게: 환경변수 키 값 + 흔한 키 모양을 가린다."""
    import os
    t = str(text)
    for k, v in os.environ.items():
        if v and len(v) >= 8 and re.search(r"KEY|TOKEN|SECRET|PASSWORD|CLIENT_ID", k):
            t = t.replace(v.strip(), "***")
    for pat in SECRET_PATTERNS:
        t = re.sub(pat, "***", t)
    return t


def to_usd(amount, currency="USD"):
    return float(amount) * float(cfg()["fx_to_usd"].get(currency.upper(), 1.0))
