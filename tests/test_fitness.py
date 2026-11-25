"""회원 운동·식단 관리 테스트 (API 키 불필요)"""
from mother import fitness


def test_repo_data_valid_and_export(tmp_path):
    data = fitness.load()
    assert fitness.validate(data) == []
    out, n = fitness.export_all(data, tmp_path)
    assert n == len(data["members"]) >= 1
    md = (tmp_path / f"{data['members'][0]['id']}.md").read_text(encoding="utf-8")
    assert "PT 이용권" in md and "주간 루틴" in md and "식단 계획" in md and "?m=" in md
    assert (tmp_path / "README.md").exists()


def test_validate_catches_errors():
    bad = {"members": [{"id": "a", "name": "x", "routine": {"월요일": [{"name": "", "sets": "3"}]}},
                       {"id": "a", "name": "y", "schedule": [{"date": "11/25"}], "photos": [{"img": "data:x"}]}]}
    errs = fitness.validate(bad)
    assert any("중복" in e for e in errs) and any("요일" in e for e in errs) and any("날짜" in e for e in errs) and any("사진" in e for e in errs)


def test_totals():
    m = {"meals": {"아침": [{"food": "a", "kcal": 100, "protein": 10}], "간식": [{"food": "b", "kcal": 50, "protein": 5}]}}
    assert fitness.totals(m) == (150, 15)
