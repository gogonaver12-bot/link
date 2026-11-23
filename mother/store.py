"""파일 기반 저장소 (DB 없이 깃허브에 그대로 커밋되어 어디서든 이어서 사용)."""
import datetime as dt
import json
import pathlib

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
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(name):
    p = DATA / name
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def spend_on(day=None):
    day = day or today()
    return round(sum(r["usd"] for r in read_jsonl("usage.jsonl") if r["ts"][:10] == day), 4)


def to_usd(amount, currency="USD"):
    return float(amount) * float(cfg()["fx_to_usd"].get(currency.upper(), 1.0))
