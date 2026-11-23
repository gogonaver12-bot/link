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
from office_suite.modules import elec_calc, estimate, plc_monitor, ppt_maker  # noqa: E402


def plug(key):
    return next(p for p in core.load_plugins() if p.key == key)


def test_all_builtin_plugins_load():
    ps = core.load_plugins()
    assert {p.key for p in ps} >= {"ppt", "estimate", "elec_calc", "plc", "worklog", "settings"}
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
    assert got[0] == ("배전반", "1600x800", "면", 2, 3500000) and got[2] == ("노무비", "", "식", 1, 280000)
    res = core.run_plugin(plug("estimate"), {"items": items, "client": "가나산업", "profit": "10"})
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
