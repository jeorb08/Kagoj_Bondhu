"""Layer 2: arithmetic / internal-consistency checks (plain code, no ML). Input: the confirmed field values."""
from __future__ import annotations

from ..rules import load_pack


def _f(code, severity, en, bn, fields):
    return {"code": code, "severity": severity, "en": en, "bn": bn, "fields": fields}


def check(doc_type: str, v: dict) -> list:
    out = []
    if doc_type == "payslip" and all(k in v for k in ("basic", "house", "medical", "transport", "food", "ot_amount", "deduction", "net")):
        exp = v["basic"] + v["house"] + v["medical"] + v["transport"] + v["food"] + v["ot_amount"] - v["deduction"]
        if abs(exp - v["net"]) > 1:
            out.append(_f("payslip.net_mismatch", "high",
                          f"Net pay is {v['net']:,.0f} but its components add up to {exp:,.0f} (gap {abs(exp - v['net']):,.0f}).",
                          f"নিট বেতন {v['net']:,.0f}, কিন্তু অংশগুলো যোগ করলে {exp:,.0f} হয় (পার্থক্য {abs(exp - v['net']):,.0f})।", ["net"]))
        if "ot_hours" in v and "ot_rate" in v and abs(v["ot_hours"] * v["ot_rate"] - v["ot_amount"]) > max(2, v["ot_hours"] * 0.01):
            out.append(_f("payslip.ot_mismatch", "medium", "OT amount does not equal OT hours × OT rate.", "ওভারটাইম টাকা = ঘণ্টা × হার, এটি মিলছে না।", ["ot_amount"]))
    if doc_type == "loan" and all(k in v for k in ("principal", "flat", "months", "inst", "total")):
        if abs(v["inst"] * v["months"] - v["total"]) > v["months"] * 0.5 + 1:
            out.append(_f("loan.total_mismatch", "high", f"Total payable {v['total']:,.0f} differs from installment × months ({v['inst'] * v['months']:,.0f}).",
                          f"মোট প্রদেয় {v['total']:,.0f}, কিন্তু কিস্তি × মাস = {v['inst'] * v['months']:,.0f}।", ["total"]))
        exp = v["principal"] * (1 + v["flat"] / 100 * v["months"] / 12)
        if abs(exp - v["total"]) > v["months"] * 0.5 + 1:
            out.append(_f("loan.rate_mismatch", "high", f"Total payable {v['total']:,.0f} does not match the printed flat rate (expected about {exp:,.0f}).",
                          f"ছাপানো সুদের হারে মোট প্রদেয় প্রায় {exp:,.0f} হওয়ার কথা, কিন্তু আছে {v['total']:,.0f}।", ["total"]))
    if doc_type == "bill" and all(k in v for k in ("units", "energy", "demand", "vat", "misc", "total")):
        slabs, left, energy = load_pack("bill")["params"]["slabs"], v["units"], 0.0
        for s in slabs:
            used = min(left, s["units"] if s["units"] is not None else 10 ** 9)
            energy += used * s["rate"]
            left -= used
            if left <= 0:
                break
        if abs(energy - v["energy"]) > 1:
            out.append(_f("bill.energy_mismatch", "high", f"Energy charge {v['energy']:,.2f} does not match the slab tariff for {v['units']:.0f} units ({energy:,.2f}).",
                          f"{v['units']:.0f} ইউনিটের স্ল্যাব হিসাবে এনার্জি চার্জ {energy:,.2f} হওয়ার কথা, আছে {v['energy']:,.2f}।", ["energy"]))
        exp = v["energy"] + v["demand"] + v["vat"] + v["misc"]
        if abs(exp - v["total"]) > 1:
            out.append(_f("bill.total_mismatch", "high", f"Total {v['total']:,.2f} but the lines add up to {exp:,.2f}.",
                          f"মোট {v['total']:,.2f}, কিন্তু লাইনগুলো যোগ করলে {exp:,.2f}।", ["total"]))
        if v["misc"] > 0:
            out.append(_f("bill.unexplained_adjustment", "low", f"An adjustment of {v['misc']:,.2f} is listed without explanation.",
                          f"{v['misc']:,.2f} টাকার সমন্বয় কোনো ব্যাখ্যা ছাড়াই বিলে আছে।", ["misc"]))
    return out
