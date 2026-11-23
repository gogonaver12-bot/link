"""Claude 호출 래퍼: 예산 차단 · 자동 캐싱 · 거절 시 서버측 폴백 · 비용 장부."""
import json

import anthropic

from . import store

_client = None
FALLBACK_OK = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-2", "claude-fable-5-1", "claude-sonnet-5-5"}


class BudgetExceeded(RuntimeError):
    pass


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


def call(tier, system, messages, tools=None, max_tokens=16000, agent="mother", schema=None):
    c = store.cfg()
    spent = store.spend_on()
    if spent >= c["budget"]["daily_usd"]:
        raise BudgetExceeded(f"오늘 예산 소진: ${spent} / ${c['budget']['daily_usd']}")
    model = c["models"][tier]
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
    resp = client().beta.messages.create(**kw)
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
    """구조화 출력: 스키마에 맞는 JSON을 보장받아 dict로 반환."""
    resp = call(tier, system, [{"role": "user", "content": prompt}], schema=schema,
                agent=agent, max_tokens=max_tokens)
    if resp.stop_reason == "refusal":
        raise RuntimeError(text_of(resp))
    return json.loads(text_of(resp))
