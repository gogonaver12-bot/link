"""새 기능 만들기 템플릿
1) 이 파일을 복사해 이름을 바꿉니다 (예: my_tool.py)
2) 아래 KEY/NAME/FIELDS/run 을 고칩니다
3) office_suite/modules/ (소스) 또는 내 문서의 회사도우미/plugins/ (exe 사용 시) 에 넣고
   프로그램 메뉴 [도움말 → 기능 다시 불러오기] → 왼쪽 목록에 자동으로 나타납니다.
"""
from office_suite.core import Field, Result

KEY = "my_tool"                 # 영문 고유 이름 (같은 KEY면 기존 기능을 덮어써 업그레이드)
NAME = "새 기능"                # 화면에 보일 이름
DESC = "무엇을 하는 기능인지 한 줄 설명"
ORDER = 60                      # 목록 순서 (작을수록 위)
FIELDS = [
    Field("name", "이름", "text", "홍길동"),
    Field("count", "개수", "number", 1),
    Field("memo", "메모", "multiline", ""),
    Field("kind", "종류", "choice", "A", choices=("A", "B")),
    Field("file", "파일", "file", ""),
    Field("ok", "확인", "check", True),
]


def run(v, ctx):
    """v: 입력값 dict, ctx.out('이름.xlsx') = 저장 경로, ctx.settings = 회사정보, ctx.ai('질문') = AI"""
    path = ctx.out("결과.txt")
    path.write_text(f"{v['name']} x {v['count']:g}\n{v['memo']}", encoding="utf-8")
    return Result(True, "완료!", [str(path)])
