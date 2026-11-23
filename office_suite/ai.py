"""선택 기능: AI 글쓰기. 저장소의 무료 우선 AI 라우터(mother) → 없으면 Claude API 직접 호출."""
import os


class AIUnavailable(RuntimeError):
    pass


def ask(prompt, system, settings):
    key = settings.get("ai_key") or os.environ.get("ANTHROPIC_API_KEY")
    try:                                    # 소스 실행 시: 무료 AI 먼저 쓰는 기존 라우터 재사용
        from mother import providers
        text, _ = providers.complete(prompt, system=system, agent="office")
        if text.strip():
            return text
    except Exception:
        pass
    if not key:
        raise AIUnavailable("AI 키가 없습니다. [회사 정보 설정]에 AI 키를 넣거나 AI 없이 직접 내용을 입력하세요.")
    try:
        import anthropic
    except ImportError as e:
        raise AIUnavailable("anthropic 패키지가 없습니다: pip install anthropic") from e
    client = anthropic.Anthropic(api_key=key)
    try:
        r = client.beta.messages.create(
            model=settings.get("ai_model") or "claude-opus-5-5",
            max_tokens=16000,
            system=system,
            output_config={"effort": "low"},          # 짧은 문서 작성 → 낮은 effort로 비용 절약
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",                      # 거절 시 서버가 다른 모델로 자동 재시도
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError as e:
        raise AIUnavailable("AI 키가 올바르지 않습니다.") from e
    except anthropic.RateLimitError as e:
        raise AIUnavailable("AI 사용량 한도 초과. 잠시 후 다시 시도하세요.") from e
    except anthropic.APIConnectionError as e:
        raise AIUnavailable("인터넷 연결을 확인하세요.") from e
    except anthropic.APIStatusError as e:
        raise AIUnavailable(f"AI 오류({e.status_code}): {e.message}") from e
    if r.stop_reason == "refusal":
        raise AIUnavailable("AI가 이 요청을 거절했습니다. 내용을 바꿔 보세요.")
    return "".join(b.text for b in r.content if b.type == "text")
