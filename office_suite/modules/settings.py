from office_suite.core import Field, Result, load_settings, save_settings

KEY = "settings"
NAME = "⚙ 회사 정보 설정"
DESC = "견적서·PPT·작업일지에 자동으로 들어갈 회사 정보 (한 번만 입력)"
ORDER = 99
FIELDS = [
    Field("company", "회사명"), Field("ceo", "대표자"), Field("biz_no", "사업자번호"),
    Field("phone", "전화번호"), Field("address", "주소"), Field("email", "이메일"),
    Field("ai_key", "AI 키 (선택)", help="Claude API 키. 없으면 AI 기능만 꺼지고 나머지는 정상 사용"),
    Field("ai_model", "AI 모델", default="claude-opus-5-5"),
    Field("naver_id", "네이버 검색 Client ID (최저가 찾기용)", help="developers.naver.com 에서 무료 발급"),
    Field("naver_secret", "네이버 검색 Client Secret"),
]


def defaults():
    return load_settings()


def run(v, ctx):
    data = load_settings()
    data.update(v)
    save_settings(data)
    return Result(True, "저장했습니다. 이제 견적서·PPT에 자동으로 들어갑니다.")
