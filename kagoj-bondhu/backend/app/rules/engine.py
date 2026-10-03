"""Deterministic checks. Pure functions: values + params in, numbers out."""
from __future__ import annotations

from datetime import date, datetime
import math
from typing import Any, Optional


def _num(values: dict, key: str, minimum: Optional[float] = None) -> float:
    if key not in values or values[key] is None:
        raise ValueError(f"missing value: {key}")
    try:
        x = float(values[key])
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number")
    if not math.isfinite(x) or abs(x) > 1e12:
        raise ValueError(f"{key} must be finite and within supported range")
    if minimum is not None and x < minimum:
        raise ValueError(f"{key} must be at least {minimum}")
    return x


def payslip(v: dict, p: dict, **_: Any) -> dict:
    basic = _num(v, "basic", 0)
    hours = _num(v, "otHours", 0)
    paid = _num(v, "otPaid", 0)
    allowance = _num(v, "eligibleAllowance", 0) if "eligibleAllowance" in v else 0
    hourly = (basic + allowance) / p["monthly_divisor"]
    rate = hourly * p["overtime_multiplier"]
    should = rate * hours
    diff = should - paid
    return {
        "hourlyWage": round(hourly, 2),
        "overtimeRate": round(rate, 2),
        "shouldPay": round(should, 2),
        "paid": round(paid, 2),
        "difference": round(max(diff, 0), 2),
        "flagged": diff > p.get("tolerance_taka", 1),
    }


def solve_monthly_rate(principal: float, installment: float, n: int) -> float:
    """Monthly rate r where installments of `installment` for n months repay `principal` exactly (IRR)."""
    if principal <= 0 or installment <= 0 or n < 1:
        raise ValueError("principal, installment and months must be positive")
    if installment * n < principal - 0.01:
        raise ValueError("Payments do not repay principal; check term, balloon payment or subsidy")
    if abs(installment * n - principal) <= 0.01:
        return 0.0
    def pv(r):
        return installment * (-math.expm1(-n * math.log1p(r))) / r
    lo, hi = 0.0, 1.0
    while pv(hi) > principal and hi < 1e6:
        hi *= 2
    if pv(hi) > principal:
        raise ValueError("Loan rate outside supported range")
    for _ in range(120):
        mid = (lo + hi) / 2
        if pv(mid) > principal:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def loan(v: dict, p: dict, **_: Any) -> dict:
    principal = _num(v, "principal", 1)
    flat = _num(v, "flat", 0)
    term = _num(v, "months", 1)
    if not term.is_integer() or term > 600:
        raise ValueError("months must be a whole number from 1 to 600")
    months = int(term)
    inst = _num(v, "inst", 1)
    fee = _num(v, "upfrontFee", 0) if "upfrontFee" in v else 0
    if fee >= principal:
        raise ValueError("upfrontFee must be less than principal")
    r = solve_monthly_rate(principal - fee, inst, months)
    nominal = r * 12 * 100
    effective = ((1 + r) ** 12 - 1) * 100
    expected = principal * (1 + flat / 100 * months / 12) / months
    total = inst * months
    return {
        "netDisbursed": round(principal - fee, 2),
        "nominalYearlyRatePct": round(nominal, 2),
        "assumptions": "Equal end-of-month payments; no balloon payment; upfront fee deducted at disbursement. 24% is a demo reference, not a legal verdict.",
        "monthlyRatePct": round(r * 100, 3),
        "realYearlyRatePct": round(nominal, 2),
        "effectiveYearlyRatePct": round(effective, 2),
        "totalRepay": round(total, 2),
        "extraPaid": round(total - principal, 2),
        "expectedInstallment": round(expected, 2),
        "installmentMatchesPrinted": abs(expected - inst) < p.get("installment_tolerance_taka", 2),
        "capPct": p["guideline_cap_percent"],
        "aboveGuideline": nominal > p["guideline_cap_percent"],
    }


def bill(v: dict, p: dict, **_: Any) -> dict:
    units = _num(v, "units", 0)
    demand = _num(v, "demand", 0)
    total = _num(v, "total", 0)
    misc = _num(v, "misc", 0) if v.get("misc") is not None else 0.0
    left, start, energy, rows = units, 0, 0.0, []
    slabs = ([{"units": 50, "rate": p["lifeline_rate"]}] if units <= 50 and "lifeline_rate" in p else p["slabs"])
    for slab in slabs:
        size = slab["units"] if slab["units"] is not None else float("inf")
        used = min(left, size)
        if used > 0:
            rows.append({"from": int(start + 1), "to": int(start + used), "units": used,
                         "rate": slab["rate"], "amount": round(used * slab["rate"], 2)})
            energy += used * slab["rate"]
            left -= used
        if size != float("inf"):
            start += size
    subtotal = energy + demand
    vat = subtotal * p["vat_percent"] / 100
    should = subtotal + vat
    diff = round(total - should, 1)
    return {
        "slabs": rows,
        "energy": round(energy, 2),
        "demand": round(demand, 2),
        "vat": round(vat, 2),
        "shouldTotal": round(should, 2),
        "charged": round(total, 2),
        "unexplainedAdjustment": round(misc, 2),
        "difference": diff,
        "flagged": abs(diff) > p["tolerance_taka"],
        "assumptions": "Historical demo tariff; subtotal excludes adjustments, arrears, rebates and meter fees. Difference requires explanation, not proof of overcharge.",
    }


def _as_date(x: Any) -> date:
    if isinstance(x, date):
        return x
    return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()


def khata(v: dict, p: dict, as_of: Optional[Any] = None, **_: Any) -> dict:
    entries = v.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries must be a non-empty list")
    today = _as_date(as_of) if as_of else date.today()
    people: dict = {}
    ordered = sorted(entries, key=lambda e: _as_date(e.get("date")))
    for e in ordered:
        name = str(e.get("name", "")).strip()
        if not name or len(name) > 160:
            raise ValueError("every entry needs a name of at most 160 characters")
        amount = _num(e, "amount", 0)
        d = _as_date(e["date"])
        if d > today:
            raise ValueError("ledger entry is after the assessment date")
        kind = e.get("kind", "credit")
        if kind not in ("credit", "payment"):
            raise ValueError("kind must be credit or payment")
        acc = people.setdefault(name, {"lots": [], "advance": 0.0})
        if kind == "credit":
            used = min(amount, acc["advance"])
            acc["advance"] -= used
            if amount > used:
                acc["lots"].append([d, amount - used])
        else:
            for lot in acc["lots"]:
                used = min(amount, lot[1])
                lot[1] -= used
                amount -= used
            acc["advance"] += amount
    out = []
    for name, acc in people.items():
        lots = [lot for lot in acc["lots"] if lot[1] > 0.005]
        if not lots:
            continue
        age = (today - lots[0][0]).days
        status = "overdue" if age > p["overdue_days"] else "watch" if age > p["warning_days"] else "ok"
        overdue = sum(a for d, a in lots if (today - d).days > p["overdue_days"])
        out.append({"name": name, "balance": round(sum(a for d, a in lots), 2),
                    "oldest": lots[0][0].isoformat(), "ageDays": age, "status": status,
                    "overdueBalance": round(overdue, 2)})
    out.sort(key=lambda c: -c["balance"])
    return {"customers": out,
            "totalOutstanding": round(sum(c["balance"] for c in out), 2),
            "overdueAmount": round(sum(c["overdueBalance"] for c in out), 2),
            "asOf": today.isoformat(), "allocation": "FIFO: payments settle oldest credit first"}
