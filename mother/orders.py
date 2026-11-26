"""크몽·숨고 주문 처리: 고객 요청을 붙여넣으면 AI가 납품할 결과물을 만든다 (reports/orders/ 에 저장 → 앱에서 복사해서 전달).
서비스 안내문은 app/kmong/listings.json (판매 글·가격·썸네일).
"""
import re

from . import providers, store

SERVICES = {
    "blog": ("블로그 원고",
             "너는 네이버 상위노출 블로그 원고 전문 작가다. 고객 요청(업종·키워드·분량)에 맞춰 원고를 쓴다. "
             "형식: ①제목 후보 3개(키워드 앞쪽) ②본문 1,800~2,500자(소제목 4~6개, 키워드 자연스럽게 5~8회, 경험담 말투, 짧은 문단) "
             "③마무리·방문 유도 ④태그 10개. 과장·허위 효능·의료 효과 단정 금지. 고객이 바로 붙여넣을 수 있게 완성본만."),
    "review": ("리뷰 답글",
               "너는 네이버 플레이스·배달앱 리뷰 답글 전문가다. 고객이 붙여넣은 리뷰마다 번호를 매겨 답글을 쓴다. "
               "규칙: 리뷰 내용을 구체적으로 짚기, 답글마다 다른 표현, 2~4문장, 따뜻하고 정중하게, 불만 리뷰는 사과+개선 약속+재방문 제안(변명 금지), "
               "가게 이름·메뉴가 있으면 자연스럽게 넣기. 개인정보·쿠폰 약속은 고객이 적은 범위 안에서만."),
    "detail": ("상세페이지 문구",
               "너는 스마트스토어·쿠팡 상세페이지 카피라이터다. 고객이 준 상품 정보로 상세페이지 문구를 쓴다. "
               "형식: ①상품명 후보 3개(검색 키워드 포함, 50자 이내) ②첫 화면 헤드카피 3안 ③고객 고민→해결 흐름의 섹션 6개(소제목+본문) "
               "④스펙 표 ⑤FAQ 5개 ⑥검색 태그 10개. 사실만, 인증·효능을 지어내지 말 것(모르면 [확인 필요]로 표시)."),
    "translate": ("외국인 안내문 번역",
                  "너는 한국 사업장의 외국인 근로자용 안내문 번역가다. 고객이 지정한 언어(없으면 네팔어·베트남어)로 번역한다. "
                  "형식: 언어마다 ①번역문 ②한국어 원문과 문장별 대조표(번호|한국어|번역) ③어려운 단어 쉬운 설명. "
                  "먼저 원문을 쉬운 한국어로 정리한 뒤 번역(안전·임금·숙소 규정은 뜻이 바뀌지 않게 정확히). "
                  "마지막 줄에 '※ AI 번역본 — 법적 효력이 필요한 문서는 공인 번역을 권장합니다'를 붙인다."),
    "ppt": ("PPT 원고",
            "너는 발표 자료 기획자다. 고객 요청으로 슬라이드별 원고를 쓴다. 형식: 슬라이드 번호·제목·핵심 3줄·추천 이미지/도표·발표자 멘트. "
            "10~15장, 첫 장 요약, 마지막 장 결론·다음 행동."),
}


def make(service, request):
    if service not in SERVICES:
        return f"서비스 종류를 골라 주세요: {', '.join(SERVICES)}"
    name, system = SERVICES[service]
    text, used = providers.complete(f"[고객 요청]\n{request}\n\n위 요청대로 납품할 결과물을 완성해서 출력.", system=system,
                                    agent=f"order_{service}", spec={"tier": "worker", "tools": [],
                                                                    "model": store.cfg().get("shorts", {}).get("writer", "auto")})
    d = store.REPORTS / "orders"
    d.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w가-힣]+", "-", request[:20]).strip("-") or "order"
    path = d / f"{store.today()}-{service}-{slug}.md"
    path.write_text(f"# 📦 {name} 납품본 — {request[:40]}\n\n> 만든 AI: {used} · 고객에게 보내기 전에 한 번 읽어보고 이름·가격 등 사실을 확인하세요\n\n"
                    f"{text}\n", encoding="utf-8")
    store.append_jsonl("orders.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "service": service, "file": path.name})
    return f"✅ {name} 납품본 완성 → 앱 보고서 탭 맨 위 ({path.name}) · 복사해서 고객에게 보내면 돼요"
