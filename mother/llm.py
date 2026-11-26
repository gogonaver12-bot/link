"""Claude 호출 래퍼: 예산 차단 · 자동 캐싱 · 거절 시 서버측 폴백 · 비용 장부."""
import json
import os

import anthropic

from . import store

_client = None
FALLBACK_OK = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-2", "claude-fable-5-1", "claude-sonnet-5-5"}


class BudgetExceeded(RuntimeError):
    pass


NO_KEY = ("AI 키가 없어요. 저장소 Settings → Secrets → Actions 에 ANTHROPIC_API_KEY "
          "또는 무료 GEMINI_API_KEY(aistudio.google.com)를 넣어주세요.")


_claude_down = None  # 크레딧 부족·키 오류가 나면 이번 실행 동안 Claude를 건너뛰고 무료 AI로 전환


DOWN_HOURS = 12  # 크레딧 부족이면 12시간 동안 Claude를 건너뛰고 그 뒤 한 번 다시 확인 (매 실행마다 실패·에러 기록 반복 방지)


def _down_saved():
    d = store.load_json("claude_down.json", {})
    if not d.get("until"):
        return None
    if store.now().isoformat(timespec="seconds") >= d["until"]:
        return None
    return d.get("why") or "Claude 크레딧 부족 → 무료 AI 사용 중"


def has_claude():
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")) or _claude_down:
        return False
    return not _down_saved()


def _check_down(e):
    """복구 안 되는 Claude 오류(잔액 부족·키 오류·권한)면 이번 실행에서 Claude를 끈다."""
    global _claude_down
    msg = str(e).lower()
    if isinstance(e, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)) or "credit balance" in msg or "billing" in msg:
        _claude_down = "Claude 크레딧 부족·키 오류 → 무료 AI로 자동 전환"
        import datetime as _dt
        store.save_json("claude_down.json", {"since": store.now().isoformat(timespec="seconds"), "why": _claude_down,
                                             "until": (store.now() + _dt.timedelta(hours=DOWN_HOURS)).isoformat(timespec="seconds")})
        store.append_jsonl("errors.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "cmd": "claude",
                                            "error": f"{type(e).__name__}: {str(e)[:300]}", "trace": "", "attempt": 1})
        return True
    return False


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    return _client


def cost_usd(model, u):
    table = store.cfg()["pricing_per_mtok"]
    i, o, cr = table.get(model, table["claude-opus-5-5"])
    usd = (u.input_tokens * i
           + (u.cache_creation_input_tokens or 0) * i * 1.25
           + (u.cache_read_input_tokens or 0) * cr
           + u.output_tokens * o) / 1e6
    stu = getattr(u, "server_tool_use", None)
    usd += (getattr(stu, "web_search_requests", 0) or 0) * 0.01  # $10 / 1000 검색
    return usd


def call(tier, system, messages, tools=None, max_tokens=16000, agent="mother", schema=None, model=None):
    c = store.cfg()
    spent = store.spend_on()
    if spent >= c["budget"]["daily_usd"]:
        raise BudgetExceeded(f"오늘 예산 소진: ${spent} / ${c['budget']['daily_usd']}")
    if not has_claude():
        raise RuntimeError(NO_KEY)
    model = model or c["models"][tier]
    output_config = {"effort": c["effort"][tier]}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    kw = dict(model=model, max_tokens=max_tokens, system=system, messages=messages,
              output_config=output_config,
              cache_control={"type": "ephemeral"})  # 반복 접두부 자동 캐싱(입력비 ~90%↓)
    if tools:
        kw["tools"] = tools
    if model in FALLBACK_OK:  # 안전분류기 오탐 거절 시 같은 호출 안에서 대체 모델이 이어받음
        kw["betas"] = ["server-side-fallback-2026-07-01"]
        kw["fallbacks"] = "default"
    try:
        resp = client().beta.messages.create(**kw)
    except anthropic.APIStatusError as e:
        if _check_down(e):
            raise RuntimeError(_claude_down) from e
        raise
    u = resp.usage
    store.append_jsonl("usage.jsonl", {
        "ts": store.now().isoformat(timespec="seconds"), "agent": agent, "model": resp.model,
        "in": u.input_tokens, "out": u.output_tokens,
        "cache_read": u.cache_read_input_tokens or 0, "usd": round(cost_usd(resp.model, u), 5)})
    return resp


def text_of(resp):
    if resp.stop_reason == "refusal":
        d = resp.stop_details
        return f"[요청 거절됨: {getattr(d, 'category', None)}]"
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def ask_json(tier, system, prompt, schema, agent="mother", max_tokens=8000):
    """구조화 출력: 스키마에 맞는 JSON을 보장받아 dict로 반환. Claude 키가 없으면 무료 AI로 대체."""
    from . import providers
    if not has_claude():
        return providers.json_complete(system, prompt, schema, agent=agent)
    try:
        resp = call(tier, system, [{"role": "user", "content": prompt}], schema=schema,
                    agent=agent, max_tokens=max_tokens)
    except BudgetExceeded:
        raise
    except Exception:
        if has_claude():
            raise
        return providers.json_complete(system, prompt, schema, agent=agent)  # Claude가 막히면 무료 AI로
    if resp.stop_reason == "refusal":
        raise RuntimeError(text_of(resp))
    return json.loads(text_of(resp))
