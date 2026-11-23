"""모든 AI 통합 라우터 (jarvis-ai-hub 방식 계승).

- 키만 넣으면 자동 연결: OpenAI 호환 방식이라 config.yaml 에 한 줄로 새 AI 추가
- 무료 AI 우선 → 실패/한도 초과 시 다음 AI로 자동 전환 → 마지막은 Claude
- 모델 이름을 몰라도 /models 목록에서 가벼운 대화 모델을 자동 선택(모델 단종 대비)
- 평가 점수가 낮은 모델은 자동 탈락(라우팅 제외)
"""
import json
import os

import requests

from . import llm, store, tools

NOT_FOR_CHAT = ("whisper", "tts", "audio", "realtime", "guard", "safety", "embed", "moderation", "transcribe",
                "image", "vision-only", "search-preview", "dall", "sora", "veo", "imagen", "rerank", "ocr")
LIGHT = ("flash", "mini", "small", "lite", "instant", "haiku", "chat")
_alive = {}


class ProviderError(RuntimeError):
    pass


def cfgp():
    return store.cfg()["providers"]


def _key(p):
    env = cfgp()[p].get("key")
    return os.getenv(env) if env else ""


def available(p):
    c = cfgp().get(p)
    if not c:
        return False
    if p == "anthropic":
        return True  # 최후 보루
    if c.get("key"):
        return bool(_key(p))
    if p not in _alive:  # 키 없는 로컬(Ollama 등)은 실제 접속 확인
        try:
            _alive[p] = requests.get(c["base"] + "/models", timeout=1.5).ok
        except requests.RequestException:
            _alive[p] = False
    return _alive[p]


def _headers(p):
    k = _key(p)
    return {"Authorization": f"Bearer {k}"} if k else {}


def _get(url, headers):
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def _post(url, headers, body):
    r = requests.post(url, headers=headers, json=body, timeout=240)
    if r.status_code >= 400:
        raise ProviderError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


def pick_model(p):
    c = cfgp()[p]
    if c.get("model"):
        return c["model"]
    if p == "anthropic":
        return store.cfg()["models"]["worker"]

    def fetch():
        d = _get(c["base"] + "/models", _headers(p))
        return sorted(m["id"].removeprefix("models/") for m in d.get("data", []))

    try:
        ids = tools._cached(f"models:{p}", 24, fetch)
    except requests.RequestException as e:
        raise ProviderError(f"{p} 모델 목록 실패: {e}") from e
    if c.get("model_filter"):
        ids = [m for m in ids if c["model_filter"] in m] or ids
    chat = [m for m in ids if not any(k in m.lower() for k in NOT_FOR_CHAT)] or ids
    if not chat:
        raise ProviderError(f"{p}: 사용 가능한 모델 없음")
    for want in c.get("prefer", []):
        hit = [m for m in chat if want.lower() in m.lower()]
        if hit:
            return hit[-1]  # 정렬상 뒤쪽 = 대체로 최신 버전
    light = [m for m in chat if any(k in m.lower() for k in LIGHT)]
    return (light or chat)[-1]


# ───────────────────────── 모델 성적표 & 탈락 ─────────────────────────
def model_stats():
    rows = store.read_jsonl("model_scores.jsonl")
    w = store.cfg()["routing"]["window"]
    out = {}
    for r in rows:
        out.setdefault(r["model"], []).append(r["score"])
    return {m: (round(sum(v[-w:]) / len(v[-w:]), 2), len(v)) for m, v in out.items()}


def demoted(model_id):
    avg, n = model_stats().get(model_id, (None, 0))
    r = store.cfg()["routing"]
    return n >= r["min_samples"] and avg < r["min_model_score"]


def record_score(model_id, score, note="", source="review"):
    store.append_jsonl("model_scores.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "model": model_id,
                                              "score": score, "note": note[:200], "source": source})


# ───────────────────────── 라우팅 ─────────────────────────
def candidates(spec):
    """에이전트 명세 → 시도할 (provider, model) 순서. 마지막은 항상 Claude."""
    want = spec.get("model", "auto")
    has_google = bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CSE_ID"))
    if spec.get("tier") == "mother":
        order = ["anthropic"]
    elif want != "auto":
        order = [want.split(":", 1)[0]]
    else:
        order = store.cfg()["routing"]["worker_order"]
    out = []
    for p in order:
        if p == "anthropic" or not available(p):
            continue
        c = cfgp()[p]
        if spec.get("tools") and not c.get("tools", True):
            continue  # 도구 호출 미지원 AI
        if "web_search" in spec.get("tools", []) and not has_google and llm.has_claude():
            continue  # 웹검색이 필요한데 구글 키 없음 → Claude 웹검색 사용 (Claude 없으면 크롤링으로 대체)
        try:
            m = want.split(":", 1)[1] if want.startswith(p + ":") else pick_model(p)
        except ProviderError:
            continue
        if not demoted(f"{p}:{m}"):
            out.append((p, m))
    if not llm.has_claude():
        return out
    if want.startswith("anthropic:"):
        last = want.split(":", 1)[1]
    else:
        last = store.cfg()["models"]["mother" if spec.get("tier") == "mother" else "worker"]
    out.append(("anthropic", last))
    return out


def _openai_tools(names, has_google):
    names = [n for n in names if n != "web_search"] + (["google_search"] if "web_search" in names and has_google else [])
    return [{"type": "function", "function": {"name": n, "description": tools.REGISTRY[n][1],
                                              "parameters": tools.REGISTRY[n][2]}}
            for n in sorted(set(names)) if n in tools.REGISTRY]


def _log(p, model, agent, u):
    price = cfgp()[p].get("price", [0, 0] if cfgp()[p].get("free") else [1.0, 4.0])
    i, o = u.get("prompt_tokens", 0) or 0, u.get("completion_tokens", 0) or 0
    store.append_jsonl("usage.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "agent": agent,
                                       "model": f"{p}:{model}", "in": i, "out": o, "cache_read": 0,
                                       "usd": round((i * price[0] + o * price[1]) / 1e6, 5)})


def run_openai(p, model, system, user, tool_names=(), agent="worker", max_turns=None):
    """OpenAI 호환 AI의 도구 루프."""
    if store.spend_on() >= store.cfg()["budget"]["daily_usd"]:
        raise llm.BudgetExceeded("오늘 예산 소진")
    max_turns = max_turns or store.cfg()["budget"]["max_tool_turns"]
    tdefs = _openai_tools(list(tool_names), bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CSE_ID")))
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    url = cfgp()[p]["base"].rstrip("/") + "/chat/completions"
    for turn in range(max_turns):
        body = {"model": model, "messages": msgs}
        if tdefs:
            body["tools"] = tdefs
        d = _post(url, _headers(p), body)
        _log(p, model, agent, d.get("usage") or {})
        m = d["choices"][0]["message"]
        calls = m.get("tool_calls") or []
        if not calls:
            return (m.get("content") or "").strip()
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
        for c in calls:
            try:
                out = tools.run_tool(c["function"]["name"], json.loads(c["function"].get("arguments") or "{}"))
            except Exception as e:  # 도구 오류는 AI가 스스로 우회하도록 전달
                out = f"error: {e}"
            msgs.append({"role": "tool", "tool_call_id": c["id"], "content": out})
        if turn == max_turns - 2:
            msgs.append({"role": "user", "content": "도구 사용 한도 도달. 지금까지 정보로 최종 결과를 작성하라."})
    return ""


def complete(prompt, system="간결하게 답하라.", agent="worker", spec=None):
    """단발 질문을 가장 싼 사용 가능 AI에 → 실패 시 다음 AI. 반환: (text, 'provider:model')."""
    spec = spec or {"tier": "worker", "tools": []}
    errs = []
    for p, m in candidates(spec):
        try:
            if p == "anthropic":
                tier = "mother" if spec.get("tier") == "mother" else "worker"
                r = llm.call(tier, system, [{"role": "user", "content": prompt}], agent=agent, model=m)
                return llm.text_of(r), f"anthropic:{r.model}"
            return run_openai(p, m, system, prompt, agent=agent, max_turns=1), f"{p}:{m}"
        except llm.BudgetExceeded:
            raise
        except Exception as e:
            errs.append(f"{p}: {e}")
    raise ProviderError(" / ".join(errs) or llm.NO_KEY)


def json_complete(system, prompt, schema, agent="worker"):
    """Claude 없이 구조화 출력: 무료 AI에 JSON 모드로 요청 → 파싱 실패 시 다음 AI."""
    errs = []
    for p, m in candidates({"tier": "worker", "tools": []}):
        try:
            body = {"model": m, "response_format": {"type": "json_object"}, "messages": [
                {"role": "system", "content": f"{system}\n반드시 아래 JSON 스키마를 따르는 JSON 객체만 출력:\n{json.dumps(schema, ensure_ascii=False)}"},
                {"role": "user", "content": prompt}]}
            d = _post(cfgp()[p]["base"].rstrip("/") + "/chat/completions", _headers(p), body)
            _log(p, m, agent, d.get("usage") or {})
            t = d["choices"][0]["message"]["content"]
            return json.loads(t[t.index("{"): t.rindex("}") + 1])
        except llm.BudgetExceeded:
            raise
        except Exception as e:
            errs.append(f"{p}: {str(e)[:100]}")
    raise RuntimeError(llm.NO_KEY if not errs else " / ".join(errs))


def status():
    rows = []
    for p, c in cfgp().items():
        ok = bool(_key(p)) if p == "anthropic" else available(p)
        rows.append(f"{'✅' if ok else '⬜'} {p:11} {'무료' if c.get('free') else '유료'}  "
                    + (c.get("note", "") if not ok else f"키 연결됨 ({c.get('key') or '로컬'})"))
    st = model_stats()
    if st:
        rows.append("\n모델 성적표 (평균점수/평가수):")
        rows += [f"  {'❌탈락' if demoted(m) else '  '} {m}: {a}점 ({n}회)" for m, (a, n) in sorted(st.items(), key=lambda x: -x[1][0])]
    return "\n".join(rows)


# ───────────────────────── 아레나: 같은 문제로 AI끼리 대결 ─────────────────────────
ARENA_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["results"],
    "properties": {"results": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["label", "score", "reason"],
        "properties": {"label": {"type": "string"}, "score": {"type": "integer", "description": "1~10"},
                       "reason": {"type": "string"}}}}},
}


def arena(task):
    entries = []
    for p in cfgp():
        if p == "anthropic" or not available(p):
            continue
        try:
            m = pick_model(p)
            entries.append((f"{p}:{m}", run_openai(p, m, "간결하고 정확하게.", task, agent="arena", max_turns=1)))
        except Exception as e:
            entries.append((f"{p}:?", f"[실패] {e}"))
    r = llm.call("worker", "간결하고 정확하게.", [{"role": "user", "content": task}], agent="arena")
    entries.append((f"anthropic:{r.model}", llm.text_of(r)))
    labels = [chr(65 + i) for i in range(len(entries))]  # 이름을 가려 공정 채점
    sheet = "\n\n".join(f"[{l}]\n{a[:3000]}" for l, (_, a) in zip(labels, entries))
    judged = llm.ask_json("mother", "너는 공정한 심사위원이다. 정확성·유용성·간결성으로 1~10점.",
                          f"과제: {task}\n\n답변들:\n{sheet}", ARENA_SCHEMA, agent="judge")["results"]
    by = {x["label"]: x for x in judged}
    out = []
    for l, (mid, _) in zip(labels, entries):
        if l in by and not mid.endswith(":?"):
            record_score(mid, by[l]["score"], by[l]["reason"], source="arena")
            out.append((mid, by[l]["score"], by[l]["reason"]))
    return sorted(out, key=lambda x: -x[1])
