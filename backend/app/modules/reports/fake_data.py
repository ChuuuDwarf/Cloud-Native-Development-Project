"""依實驗項目產生示範用的假量測數據。

對應前端的實驗項目分組：
- 材料分析實驗室：EDX / FIB / SEM
- 電性測試實驗室：CV / IV / Probe
- 可靠度實驗室：ESD / HTOL / TC

回傳 ``{欄位: 顯示字串}``，存進 ``reports.experiment_data``（每個實驗項目一組）。
未知項目給通用數據，不會壞。純示範資料，不是真實量測。
"""

from __future__ import annotations

import random


def _r(low: float, high: float, digits: int = 2) -> float:
    return round(random.uniform(low, high), digits)


def _edx() -> dict[str, str]:
    si = _r(55, 70, 1)
    o = _r(18, 30, 1)
    al = _r(2, 8, 1)
    other = round(max(0.0, 100 - si - o - al), 1)
    return {
        "Si 含量": f"{si} %",
        "O 含量": f"{o} %",
        "Al 含量": f"{al} %",
        "其他元素": f"{other} %",
        "加速電壓": "20 kV",
    }


def _fib() -> dict[str, str]:
    return {
        "切割深度": f"{_r(1.0, 8.0, 2)} μm",
        "研磨時間": f"{random.randint(5, 40)} min",
        "離子束電流": f"{_r(0.1, 9.3, 2)} nA",
    }


def _sem() -> dict[str, str]:
    return {
        "放大倍率": f"{random.choice([5000, 10000, 20000, 50000])} x",
        "解析度": f"{_r(1.0, 5.0, 1)} nm",
        "加速電壓": f"{random.choice([5, 10, 15, 20])} kV",
        "影像張數": str(random.randint(3, 12)),
    }


def _cv() -> dict[str, str]:
    return {
        "平帶電壓 Vfb": f"{_r(-1.5, -0.2, 3)} V",
        "最大電容 Cmax": f"{_r(80, 200, 1)} pF",
        "最小電容 Cmin": f"{_r(10, 60, 1)} pF",
        "界面態密度 Dit": f"{_r(1.0, 9.9, 2)}e10 cm⁻²eV⁻¹",
    }


def _iv() -> dict[str, str]:
    return {
        "閾值電壓 Vth": f"{_r(0.3, 0.9, 3)} V",
        "導通電流 Ion": f"{_r(1.0, 50.0, 2)} mA",
        "關斷電流 Ioff": f"{_r(0.1, 9.9, 2)} nA",
        "漏電流": f"{_r(0.1, 9.9, 2)} pA",
    }


def _probe() -> dict[str, str]:
    return {
        "接觸電阻": f"{_r(0.5, 50.0, 2)} Ω",
        "片電阻": f"{_r(10, 200, 1)} Ω/sq",
        "量測點數": str(random.randint(9, 49)),
    }


def _esd() -> dict[str, str]:
    return {
        "HBM 通過電壓": f"{random.choice([2000, 4000, 6000, 8000])} V",
        "MM 通過電壓": f"{random.choice([200, 400, 600])} V",
        "CDM 通過電壓": f"{random.choice([500, 750, 1000])} V",
        "判定": random.choice(["Pass", "Pass", "Fail"]),
    }


def _htol() -> dict[str, str]:
    fails = random.randint(0, 2)
    return {
        "測試時數": f"{random.choice([168, 500, 1000])} hr",
        "樣品數": str(random.randint(45, 77)),
        "失效數": str(fails),
        "FIT": f"{_r(1.0, 50.0, 1)}",
    }


def _tc() -> dict[str, str]:
    return {
        "溫度範圍": "-40 ~ 125 ℃",
        "循環數": f"{random.choice([200, 500, 1000])}",
        "失效數": str(random.randint(0, 3)),
        "分層比例": f"{_r(0.0, 5.0, 2)} %",
    }


_GENERATORS = {
    "EDX": _edx,
    "FIB": _fib,
    "SEM": _sem,
    "CV": _cv,
    "IV": _iv,
    "Probe": _probe,
    "ESD": _esd,
    "HTOL": _htol,
    "TC": _tc,
}


def generate_experiment_data(item: str) -> dict[str, str]:
    """為單一實驗項目產生假數據；未知項目給通用量測值。"""
    gen = _GENERATORS.get(item)
    if gen is not None:
        return gen()
    return {
        "量測值": f"{_r(0, 100, 2)}",
        "標準差": f"{_r(0, 5, 3)}",
        "樣本數": str(random.randint(3, 30)),
    }


def generate_for_items(items: list[str]) -> dict[str, dict[str, str]]:
    """為多個實驗項目產生 ``{項目: {欄位: 值}}``。"""
    return {item: generate_experiment_data(item) for item in items if item}
