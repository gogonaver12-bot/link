"""회사 도우미 오프라인 테스트 (네트워크·AI 키 불필요)."""
import os
import socket
import struct
import tempfile
import threading

os.environ["OFFICE_HOME"] = tempfile.mkdtemp(prefix="office_")

import pytest  # noqa: E402

pptx = pytest.importorskip("pptx")
openpyxl = pytest.importorskip("openpyxl")

from office_suite import core  # noqa: E402
from office_suite.modules import elec_calc, estimate, plc_monitor, ppt_maker, price_search  # noqa: E402


def plug(key):
    return next(p for p in core.load_plugins() if p.key == key)


def test_all_builtin_plugins_load():
    ps = core.load_plugins()
    assert {p.key for p in ps} >= {"ppt", "estimate", "price", "elec_calc", "plc", "worklog", "settings"}
    assert not [p for p in ps if p.error]


def test_ppt_outline_and_file():
    s = ppt_maker.parse("# 개요\n- 2주차 작업\n  - 세부\n| 가 | 나 |\n|---|---|\n| 1 | 2 |\n그림: 없는파일.png")
    assert s[0]["bullets"] == [(0, "2주차 작업"), (1, "세부")]
    assert s[0]["table"] == [["가", "나"], ["1", "2"]] and s[0]["images"] == ["없는파일.png"]
    res = core.run_plugin(plug("ppt"), {"title": "테스트 보고"})
    assert res.ok, res.message
    prs = pptx.Presentation(res.files[0])
    assert len(prs.slides) == 4  # 표지 + 샘플 3장
    texts = " ".join(sh.text_frame.text for sl in prs.slides for sh in sl.shapes if sh.has_text_frame)
    assert "테스트 보고" in texts and "주요 작업" in texts


def test_won_korean():
    assert estimate.won_kor(1234500) == "일백이십삼만사천오백"
    assert estimate.won_kor(100000000) == "일억"
    assert estimate.won_kor(20500) == "이만오백"


def test_estimate_excel():
    items = "배전반, 1600x800, 면, 2, 3,500,000\n케이블\tCV 4C\tm\t100\t18500\n노무비, 1, 280000"
    got = estimate.parse_items(items)
    assert got[0] == ("배전반", "1600x800", "면", 2, 3500000, 0) and got[2] == ("노무비", "", "식", 1, 280000, 0)
    res = core.run_plugin(plug("estimate"), {"items": items, "client": "가나산업", "profit": "10"})
    assert len(res.files) == 1  # 원가 없으면 마진분석 파일 없음
    assert res.ok, res.message
    # (7,000,000 + 1,850,000 + 280,000) = 9,130,000 → 이윤 913,000 → 10,043,000 → VAT 1,004,300 → 11,047,300
    assert "11,047,300" in res.message
    ws = openpyxl.load_workbook(res.files[0]).active
    formulas = [c.value for c in ws["G"] if isinstance(c.value, str) and c.value.startswith("=")]
    assert formulas[0] == "=E12*F12" and any("SUM" in f for f in formulas)
    with pytest.raises(ValueError):
        estimate.parse_items("이상한 줄")


def test_elec_calc():
    i = elec_calc.current("3상 3선식", 380, 10, 0.9)
    assert abs(i - 16.88) < 0.01
    need, size, _ = elec_calc.cable_for_drop("3상 3선식", 380, 100, 50, 3)
    assert abs(need - 30.8 * 100 * 50 / (1000 * 11.4)) < 1e-6 and size == 16
    assert abs(elec_calc.capacitor_kvar(100, 0.8, 0.95) - 42.13) < 0.01
    res = core.run_plugin(plug("elec_calc"), {})
    assert res.ok and "부하 전류" in res.message
    assert not core.run_plugin(plug("elec_calc"), {"pf": "1.5"}).ok


def fake_modbus_server():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def serve():
        conn, _ = srv.accept()
        with conn:
            while True:
                hdr = conn.recv(7)
                if len(hdr) < 7:
                    return
                tid, _, length, unit = struct.unpack(">HHHB", hdr)
                func, start, count = struct.unpack(">BHH", conn.recv(length - 1))
                if func == 3:
                    data = struct.pack(f">{count}H", *[start + k for k in range(count)])
                else:
                    bits = sum(1 << k for k in range(count) if k % 2 == 0)
                    data = bits.to_bytes((count + 7) // 8, "little")
                pdu = bytes([func, len(data)]) + data
                conn.sendall(struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu)
    threading.Thread(target=serve, daemon=True).start()
    return srv.getsockname()[1]


def test_modbus_client_reads():
    port = fake_modbus_server()
    c = plc_monitor.ModbusTCP("127.0.0.1", port, 1)
    assert c.read(3, 100, 4) == [100, 101, 102, 103]
    assert c.read(1, 0, 5) == [1, 0, 1, 0, 1]
    with pytest.raises(ValueError):
        c.read(6, 0, 1)  # 쓰기 함수는 막힘
    c.close()


def test_plc_plugin_modbus_and_sim():
    port = fake_modbus_server()
    res = core.run_plugin(plug("plc"), {"mode": "Modbus TCP", "ip": "127.0.0.1", "port": port,
                                        "start": "10", "count": 3, "repeat": 2, "interval": 0.1})
    assert res.ok, res.message
    assert "10 = 10" in res.message.replace("  ", " ").replace("       ", "")
    ws = openpyxl.load_workbook(res.files[0]).active
    assert ws.max_row == 3 and ws["B1"].value == "10"
    sim = core.run_plugin(plug("plc"), {"repeat": 1, "save": False})
    assert sim.ok and not sim.files
    bad = core.run_plugin(plug("plc"), {"mode": "Modbus TCP", "ip": "127.0.0.1", "port": 1, "repeat": 1})
    assert not bad.ok and "연결 실패" in bad.message


def test_worklog_appends():
    p = plug("worklog")
    for _ in range(2):
        res = core.run_plugin(p, {"day": "2026-11-23", "site": "○○공장", "work": "분전반 결선"})
        assert res.ok, res.message
    assert openpyxl.load_workbook(res.files[0]).active.max_row == 3
    assert not core.run_plugin(p, {"day": "11/23", "work": "x"}).ok


def test_settings_and_external_plugin():
    core.run_plugin(plug("settings"), {"company": "한빛전기"})
    assert core.load_settings()["company"] == "한빛전기"
    core.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    (core.PLUGIN_DIR / "hello.py").write_text(
        "from office_suite.core import Field\nKEY='hello'\nNAME='인사'\nFIELDS=[Field('n','이름')]\n"
        "def run(v, ctx):\n    return f\"안녕 {v['n']} / {ctx.settings['company']}\"\n", encoding="utf-8")
    (core.PLUGIN_DIR / "broken.py").write_text("import 없는모듈\n", encoding="utf-8")
    ps = {p.key: p for p in core.load_plugins()}
    assert core.run_plugin(ps["hello"], {"n": "아버지"}).message == "안녕 아버지 / 한빛전기"
    assert ps["broken"].error and not core.run_plugin(ps["broken"], {}).ok


def test_estimate_margin():
    assert estimate.price_from_margin(80000, 20) == 100000
    assert estimate.price_from_margin(15200, 20) == 19000
    items = "배전반, A, 면, 2, 3500000, 2800000\n케이블, 4C, m, 100, , 15200\n노무비, 내선, 인, 1, 280000"
    res = core.run_plugin(plug("estimate"), {"items": items, "client": "다라", "margin": "20"})
    assert res.ok, res.message
    # 매출 7,000,000 + 1,900,000 + 280,000 = 9,180,000 / 원가 5,600,000 + 1,520,000 = 7,120,000
    assert "이익 ₩2,060,000" in res.message and "원가 미입력 1개" in res.message
    quote, margin = (openpyxl.load_workbook(f).active for f in res.files)
    quote_text = " ".join(str(c.value) for row in quote.iter_rows() for c in row if c.value)
    assert "2800000" not in quote_text and "원가" not in quote_text  # 견적서에 원가 노출 금지
    assert margin["G4"].value == 2800000 and margin["J4"].value.startswith("=IF")
    bad = core.run_plugin(plug("estimate"), {"items": "케이블, 4C, m, 100, , 15200", "margin": "0"})
    assert not bad.ok and "마진율" in bad.message
    loss = core.run_plugin(plug("estimate"), {"items": "차단기, 3P, EA, 1, 50000, 60000"})
    assert "원가보다 싸게" in loss.message


def test_price_search(monkeypatch, tmp_path):
    def fake_fetch(query, cid, secret, display=80):
        return {"items": [
            {"title": "<b>CV</b> 케이블 4C 25SQ 1m", "lprice": "16000", "mallName": "A몰", "link": "http://a"},
            {"title": "케이블 타이 100개", "lprice": "900", "mallName": "B몰", "link": "http://b"},  # 엉뚱한 상품
            {"title": "중고 CV 케이블 4C 25sq", "lprice": "5000", "mallName": "C몰", "link": "http://c"},
            {"title": "CV케이블 4C 25㎟", "lprice": "15500", "mallName": "D몰", "link": "http://d"}]}
    monkeypatch.setattr(price_search, "naver_fetch", fake_fetch)
    monkeypatch.setattr(price_search.time, "sleep", lambda s: None)
    got = price_search.naver_search("CV 케이블 4C 25sq", "id", "sec", ["중고"])
    assert [g["vendor"] for g in got] == ["D몰", "A몰"]
    assert price_search.parse_query("하이박스 300x400 × 2") == ("하이박스 300x400", 2.0)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "한일전기"
    ws.append(["거래처 단가표"])
    ws.append(["품명", "규격", "단위", "단가"])
    ws.append(["CV 케이블", "4C 25sq", "m", "14,800"])
    ws.append(["배선용차단기", "ABN103c", "EA", 61000])
    xlsx = tmp_path / "단가.xlsx"
    wb.save(xlsx)
    csvf = tmp_path / "대한상사.csv"
    csvf.write_bytes("품명,규격,단가\nCV 케이블,4C 25sq,15100\n".encode("cp949"))
    items = price_search.load_pricelist(xlsx) + price_search.load_pricelist(csvf)
    assert {i["vendor"] for i in items} == {"한일전기", "대한상사"}

    core.save_settings({**core.load_settings(), "naver_id": "id", "naver_secret": "sec"})
    res = core.run_plugin(plug("price"), {"items": "CV 케이블 4C 25sq × 100\n없는물건 xyz", "pricelist": str(xlsx)})
    assert res.ok, res.message
    assert "14,800원  한일전기" in res.message and "못 찾음" in res.message
    assert "CV 케이블 4C 25sq, , m, 100, , 14800" in res.message
    est = core.run_plugin(plug("estimate"), {"items": "CV 케이블 4C 25sq, , m, 100, , 14800", "margin": "20"})
    assert est.ok and "1,850,000" in est.message  # 14800/0.8 = 18500 × 100
    only_list = core.run_plugin(plug("price"), {"items": "x", "source": "거래처 단가표만"})
    assert not only_list.ok and "단가표" in only_list.message
