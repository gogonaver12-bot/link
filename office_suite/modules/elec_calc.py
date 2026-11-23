"""전기 계산기: 부하전류, 전압강하 기준 전선 굵기, 차단기 참고값, 역률 개선 콘덴서."""
import math
from datetime import datetime

from office_suite.core import Field, Result

KEY = "elec_calc"
NAME = "⚡ 전기 계산기"
DESC = "전류·전선 굵기(전압강하)·차단기·역률개선 콘덴서를 한 번에 계산 (구리선 기준, 참고용)"
ORDER = 30
SYSTEMS = {  # 이름: (계수 K, 상수, 전압강하 기준전압 = V / div)
    "3상 3선식": (30.8, 3, 1), "3상 4선식": (17.8, 3, math.sqrt(3)),
    "단상 2선식": (35.6, 1, 1), "단상 3선식": (17.8, 1, 2),
}
SIZES = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630]
BREAKERS = [15, 20, 30, 40, 50, 60, 75, 100, 125, 150, 175, 200, 225, 250, 300, 350, 400,
            500, 600, 630, 700, 800, 1000, 1200, 1600, 2000, 2500, 3200, 4000]
FIELDS = [
    Field("system", "배전 방식", "choice", "3상 3선식", choices=tuple(SYSTEMS)),
    Field("volt", "전압 (V)", "number", 380),
    Field("kw", "부하 용량 (kW)", "number", 30),
    Field("pf", "역률 (0~1)", "number", 0.85),
    Field("length", "전선 길이 (m, 편도)", "number", 80),
    Field("drop", "허용 전압강하 (%)", "number", 3, help="KEC: 조명 3%, 기타 5% (100m 이하 기준)"),
    Field("target_pf", "목표 역률 (콘덴서 계산)", "number", 0.95),
]


def current(system, v, kw, pf):
    _, ph, _ = SYSTEMS[system]
    return kw * 1000 / ((math.sqrt(3) if ph == 3 else 1) * v * pf)


def vdrop(system, length, amps, mm2):
    return SYSTEMS[system][0] * length * amps / (1000 * mm2)


def cable_for_drop(system, v, length, amps, drop_pct):
    k, _, div = SYSTEMS[system]
    allowed = v / div * drop_pct / 100
    need = k * length * amps / (1000 * allowed)
    return need, next((s for s in SIZES if s >= need), None), allowed


def capacitor_kvar(kw, pf1, pf2):
    if pf2 <= pf1:
        return 0.0
    return kw * (math.tan(math.acos(pf1)) - math.tan(math.acos(pf2)))


def run(v, ctx):
    if not (0 < v["pf"] <= 1 and 0 < v["target_pf"] <= 1):
        return Result(False, "역률은 0보다 크고 1 이하로 입력하세요. (예: 0.85)")
    if v["volt"] <= 0 or v["kw"] <= 0 or v["drop"] <= 0 or v["length"] < 0:
        return Result(False, "전압·부하 용량·허용 전압강하는 0보다 커야 합니다.")
    sys_ = v["system"]
    i = current(sys_, v["volt"], v["kw"], v["pf"])
    need, size, allowed = cable_for_drop(sys_, v["volt"], v["length"], i, v["drop"])
    brk = next((b for b in BREAKERS if b >= i * 1.25), None)
    qc = capacitor_kvar(v["kw"], v["pf"], v["target_pf"])
    lines = [
        f"■ 조건: {sys_} {v['volt']:g}V, {v['kw']:g}kW, 역률 {v['pf']:g}, 길이 {v['length']:g}m",
        f"① 부하 전류: {i:.1f} A",
        f"② 전압강하 {v['drop']:g}% 이내 전선: 계산 {need:.1f}㎟ → 규격 {size or '630㎟ 초과(병렬 포설 검토)'}㎟",
    ]
    if size:
        e = vdrop(sys_, v["length"], i, size)
        lines.append(f"   └ {size}㎟ 사용 시 전압강하 {e:.2f}V ({e / (allowed / v['drop']) :.2f}%) / 허용 {allowed:.1f}V")
    lines += [
        f"③ 차단기 참고: 전류×1.25 = {i * 1.25:.1f}A → 표준 {brk or '4000A 초과'}A",
        "   └ 반드시 전선 허용전류(KEC 표) ≥ 차단기 정격 ≥ 부하전류 확인",
        f"④ 역률 {v['pf']:g} → {v['target_pf']:g} 개선 콘덴서: {qc:.1f} kVA",
        "※ 구리선·내선규정 간이식 기준 참고값입니다. 최종 설계는 KEC 및 제조사 자료로 확인하세요.",
    ]
    msg = "\n".join(lines)
    with (ctx.out_dir / "계산기록.txt").open("a", encoding="utf-8") as fp:
        fp.write(f"[{datetime.now():%Y-%m-%d %H:%M}]\n{msg}\n\n")
    return Result(True, msg, [str(ctx.out_dir / "계산기록.txt")])
