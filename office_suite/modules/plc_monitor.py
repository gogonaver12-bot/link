"""PLC 모니터 (읽기 전용 — 설비에 값을 쓰지 않으므로 안전).
Modbus TCP: LS XGT(FEnet)·미쓰비시 FX5/Q·지멘스·인버터 등 대부분 지원 / MC 프로토콜: 미쓰비시 전용."""
import math
import random
import socket
import struct
import time
from datetime import datetime

from openpyxl import Workbook

from office_suite.core import Field, Result

KEY = "plc"
NAME = "🔌 PLC 모니터 (읽기 전용)"
DESC = "PLC 값을 주기적으로 읽어 화면에 보여주고 엑셀로 기록. 설비를 움직이는 '쓰기' 기능은 일부러 없음"
ORDER = 35
MODES = ("시뮬레이션 (연습용)", "Modbus TCP", "미쓰비시 MC 프로토콜")
AREAS = {"보유 레지스터 (4xxxx, D/HR)": 3, "입력 레지스터 (3xxxx)": 4, "코일 (0xxxx, 출력)": 1, "입력 접점 (1xxxx)": 2}
FIELDS = [
    Field("mode", "통신 방식", "choice", MODES[0], choices=MODES),
    Field("ip", "PLC IP 주소", "text", "192.168.0.10"),
    Field("port", "포트 (Modbus 502 / MC는 PLC 설정값)", "number", 502),
    Field("unit", "국번 (Modbus Unit ID)", "number", 1),
    Field("area", "Modbus 영역", "choice", next(iter(AREAS)), choices=tuple(AREAS)),
    Field("start", "시작 주소 (Modbus: 0부터 숫자 / MC: D100, M0 등)", "text", "0"),
    Field("count", "읽을 개수", "number", 10),
    Field("repeat", "반복 횟수", "number", 5),
    Field("interval", "간격 (초)", "number", 1),
    Field("save", "엑셀로 기록 저장", "check", True),
]


class ModbusError(RuntimeError):
    pass


def _recv(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ModbusError("PLC가 연결을 끊었습니다.")
        buf += chunk
    return buf


class ModbusTCP:
    """읽기 함수(1~4번)만 구현한 최소 Modbus TCP 클라이언트."""

    def __init__(self, ip, port=502, unit=1, timeout=3):
        self.sock = socket.create_connection((ip, int(port)), timeout=timeout)
        self.unit, self.tid = int(unit), 0

    def read(self, func, start, count):
        if func not in (1, 2, 3, 4):
            raise ValueError("읽기 전용: 함수 1~4만 허용")
        self.tid = (self.tid + 1) % 65536
        pdu = struct.pack(">BHH", func, int(start), int(count))
        self.sock.sendall(struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit) + pdu)
        _, _, length, _ = struct.unpack(">HHHB", _recv(self.sock, 7))
        body = _recv(self.sock, length - 1)
        if body[0] & 0x80:
            raise ModbusError(f"PLC 오류 응답 코드 {body[1]} (주소/개수/국번 확인)")
        data = body[2:2 + body[1]]
        if func in (3, 4):
            return list(struct.unpack(f">{count}H", data[:2 * count]))
        return [(data[i // 8] >> (i % 8)) & 1 for i in range(count)]

    def close(self):
        self.sock.close()


class MCProtocol:
    def __init__(self, ip, port):
        try:
            import pymcprotocol
        except ImportError as e:
            raise RuntimeError("MC 프로토콜 부품이 없습니다: pip install pymcprotocol") from e
        self.mc = pymcprotocol.Type3E(plctype="Q")
        self.mc.connect(ip, int(port))

    def read(self, device, count):
        bit = device[:1].upper() in "MXYLBFSV" and not device.upper().startswith(("SD", "SW"))
        fn = self.mc.batchread_bitunits if bit else self.mc.batchread_wordunits
        return fn(headdevice=device.upper(), readsize=int(count))

    def close(self):
        self.mc.close()


class Simulator:
    def __init__(self):
        self.t = 0

    def read(self, count):
        self.t += 1
        return [int(500 + 400 * math.sin((self.t + k) / 3)) if k % 2 == 0 else random.randint(0, 1)
                for k in range(count)]

    def close(self):
        pass


def _labels(v, n):
    if v["mode"] == MODES[2]:
        dev = v["start"].strip().upper()
        head = dev.rstrip("0123456789")
        base = int(dev[len(head):] or 0)
        return [f"{head}{base + k}" for k in range(n)]
    base = int(float(v["start"] or 0)) if v["mode"] == MODES[1] else 0
    return [f"{base + k}" for k in range(n)]


def run(v, ctx):
    n, rep = max(1, min(int(v["count"]), 125)), max(1, min(int(v["repeat"]), 100000))
    mode = v["mode"]
    try:
        if mode == MODES[0]:
            dev = Simulator()
            read = lambda: dev.read(n)
        elif mode == MODES[1]:
            dev = ModbusTCP(v["ip"].strip(), v["port"], v["unit"])
            func, start = AREAS.get(v["area"], 3), int(float(v["start"] or 0))
            read = lambda: dev.read(func, start, n)
        else:
            dev = MCProtocol(v["ip"].strip(), v["port"])
            read = lambda: dev.read(v["start"].strip(), n)
    except (OSError, socket.timeout) as e:
        return Result(False, f"PLC 연결 실패: {e}\n확인: ① IP/포트 ② PC와 PLC가 같은 네트워크 ③ PLC 이더넷 설정에서 해당 통신 허용")
    labels = _labels(v, n)
    rows = []
    try:
        for k in range(rep):
            rows.append([datetime.now().strftime("%H:%M:%S")] + list(read()))
            if k < rep - 1:
                time.sleep(max(0.1, v["interval"]))
    except Exception as e:
        if not rows:
            return Result(False, f"읽기 실패: {e}")
        rows.append([f"중단: {e}"])
    finally:
        dev.close()
    good = [r for r in rows if len(r) > 1]
    last = good[-1] if good else []
    msg = [f"{mode} · {len(good)}회 읽음 (마지막 {last[0] if last else '-'})"]
    msg += [f"  {lab:>8} = {val}" for lab, val in zip(labels, last[1:])]
    if len(rows) != len(good):
        msg.append(rows[-1][0])
    files = []
    if v["save"] and good:
        wb = Workbook()
        ws = wb.active
        ws.title = "PLC기록"
        ws.append(["시각"] + labels)
        for r in good:
            ws.append(r)
        path = ctx.out("PLC기록.xlsx")
        wb.save(path)
        files.append(str(path))
    return Result(bool(good), "\n".join(msg), files)
