"""플러그인 로더·설정·실행. 새 기능 = modules/ 또는 ~/회사도우미/plugins/ 에 .py 파일 하나."""
import importlib
import importlib.util
import json
import os
import pkgutil
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("OFFICE_HOME") or Path.home() / "회사도우미")
OUT = HOME / "결과물"
PLUGIN_DIR = HOME / "plugins"
SETTINGS = HOME / "settings.json"

DEFAULT_SETTINGS = {
    "company": "", "ceo": "", "biz_no": "", "phone": "", "address": "", "email": "",
    "ai_key": "", "ai_model": "claude-opus-5-5", "naver_id": "", "naver_secret": "",
}


@dataclass
class Field:
    key: str
    label: str
    kind: str = "text"          # text | multiline | number | choice | file | check
    default: object = ""
    choices: tuple = ()
    help: str = ""


@dataclass
class Result:
    ok: bool
    message: str
    files: list = field(default_factory=list)


@dataclass
class Plugin:
    key: str
    name: str
    desc: str = ""
    order: int = 50
    fields: list = field(default_factory=list)
    run: object = None
    module: object = None
    error: str = ""


class Ctx:
    """플러그인에 넘겨주는 도구 모음."""

    def __init__(self, key):
        self.settings = load_settings()
        self.out_dir = OUT / key
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def out(self, name):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem, dot, ext = name.rpartition(".")
        return self.out_dir / f"{stem}_{stamp}.{ext}" if dot else self.out_dir / f"{name}_{stamp}"

    def ai(self, prompt, system="간결한 한국어로 답하라."):
        from . import ai
        return ai.ask(prompt, system, self.settings)


def load_settings():
    data = dict(DEFAULT_SETTINGS)
    try:
        data.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return data


def save_settings(data):
    HOME.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _wrap(mod, key):
    if not hasattr(mod, "run"):
        return None
    return Plugin(key=getattr(mod, "KEY", key), name=getattr(mod, "NAME", key),
                  desc=getattr(mod, "DESC", ""), order=getattr(mod, "ORDER", 50),
                  fields=list(getattr(mod, "FIELDS", [])), run=mod.run, module=mod)


def load_plugins():
    """내장(modules/) + 외부(~/회사도우미/plugins/*.py). 고장난 기능은 [오류]로 표시만 하고 나머지는 정상 동작."""
    from . import modules as pkg
    names = set(getattr(pkg, "BUILTIN", []))
    names |= {n for _, n, _ in pkgutil.iter_modules(pkg.__path__)}
    plugins = {}
    for n in sorted(names):
        if n.startswith("_"):
            continue
        try:
            p = _wrap(importlib.import_module(f"{pkg.__name__}.{n}"), n)
        except Exception as e:
            p = Plugin(key=n, name=n, error=f"{type(e).__name__}: {e}")
        if p:
            plugins[p.key] = p
    if PLUGIN_DIR.is_dir():
        for f in sorted(PLUGIN_DIR.glob("*.py")):
            if f.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"office_ext_{f.stem}", f)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
                p = _wrap(mod, f.stem)
            except Exception as e:
                p = Plugin(key=f.stem, name=f.stem, error=f"{type(e).__name__}: {e}")
            if p:
                plugins[p.key] = p          # 같은 KEY면 외부 파일이 내장 기능을 덮어씀(업그레이드)
    return sorted(plugins.values(), key=lambda p: (p.order, p.name))


def coerce(f, raw):
    if f.kind == "number":
        s = str(raw).replace(",", "").strip()
        return float(s) if s else float(f.default or 0)
    if f.kind == "check":
        return raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "y", "yes", "예", "on")
    return "" if raw is None else str(raw)


def run_plugin(plug, raw):
    if plug.error:
        return Result(False, f"이 기능은 불러오지 못했습니다: {plug.error}")
    vals = {}
    try:
        for f in plug.fields:
            vals[f.key] = coerce(f, raw.get(f.key, raw.get(f.label, f.default)))
    except ValueError as e:
        return Result(False, f"숫자 칸에 숫자가 아닌 값이 있습니다: {e}")
    try:
        r = plug.run(vals, Ctx(plug.key))
    except Exception as e:
        log = HOME / "error.log"
        HOME.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fp:
            fp.write(f"\n[{datetime.now():%F %T}] {plug.key}\n{traceback.format_exc()}")
        return Result(False, f"오류: {e}\n(자세한 내용: {log})")
    if isinstance(r, Result):
        return r
    if isinstance(r, tuple):
        return Result(True, r[0], [str(x) for x in r[1]])
    return Result(True, str(r))
