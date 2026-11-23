"""마사지 부위 지도(massage/index.html) 데이터베이스 무결성 검사."""
import json
import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[1] / "massage" / "index.html"


def load_db():
    text = HTML.read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="massage-db">(.*?)</script>', text, re.S)
    assert m, "DB 블록이 없습니다"
    return json.loads(m.group(1))


def test_every_region_has_protocol_and_shape():
    db = load_db()
    names = set(db["names"])
    assert set(db["protocols"]) == names
    assert {s["k"] for s in db["shapes"]} == names
    assert all(s["s"] in {"L", "R", "C"} and s["v"] in {"f", "b"} for s in db["shapes"])


def test_targets_and_refs_exist():
    db = load_db()
    names, refs = set(db["names"]), db["refs"]
    for key, p in db["protocols"].items():
        assert p["cert"] in {"mod", "low", "vlow", "none"}, key
        assert p["targets"] and p["steps"] and p["caution"], key
        for tk, why in p["targets"]:
            assert tk in names and why, (key, tk)
        for rid in p["refs"]:
            assert rid in refs, (key, rid)
        if p["cert"] != "none":
            assert p["refs"], f"{key}: 근거 등급이 있는데 논문이 없음"


def test_refs_well_formed():
    db = load_db()
    allowed = set(db["names"]) | set(db["tagNames"])
    for rid, r in db["refs"].items():
        assert r["url"].startswith("https://"), rid
        assert r["t"] and r["ko"] and 1990 < r["y"] < 2030, rid
        assert set(r["tags"]) <= allowed, rid


def test_patterns_compile_and_match_examples():
    db = load_db()
    kws = [(re.compile(k["re"]), k.get("strip"), k["keys"]) for k in db["keywords"]]

    def keys_for(text):
        found = set()
        for rx, strip, keys in kws:
            t = re.sub(strip, " ", text) if strip else text
            if rx.search(t):
                found.update(keys)
        return found

    assert "neck" in keys_for("뒷목이 뻐근해요")
    assert "neck" not in keys_for("손목이 시큰해요")
    assert "wrist" in keys_for("손목이 시큰해요")
    assert "foot" in keys_for("아침 첫발 디딜 때 뒤꿈치가 아파요")
    assert "abdomen" not in keys_for("운동 후 알 배겼어요")
    flags = {f["id"]: re.compile(f["re"]) for f in db["flags"]}
    assert flags["cauda"].search("소변 보기가 어려워요")
    assert flags["dvt"].search("한쪽 종아리가 붓고 뜨거워요")
    for v in db["phase"].values():
        re.compile(v)
    re.compile(db["doms"])
