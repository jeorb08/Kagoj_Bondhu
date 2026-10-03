"""Synthetic documents + tampering + phone-photo simulation.

Everything here is FICTIONAL (invented names, companies and numbers). No real documents are used,
which is what the hackathon rules require, and because we create the edits ourselves we know the ground truth.

Pipeline for every sample (genuine AND tampered, identical for both so the classifier cannot learn a shortcut):
    render -> [pre-capture edit] -> camera (warp, blur, noise, lighting) -> JPEG q1 -> [post-capture edit] -> JPEG q2
"""
from __future__ import annotations

import io
import random
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..rules import load_pack

W, H = 720, 960
FONT_DIR = Path(__file__).parent / "fonts"
FONTS = {"sans": "DejaVuSans.ttf", "serif": "DejaVuSerif.ttf", "mono": "DejaVuSansMono.ttf"}
_font_cache: dict = {}

FIRST = ["Rina", "Karim", "Nasima", "Salam", "Jamal", "Fatema", "Rahim", "Sumon", "Shilpi", "Mizan", "Tania", "Habib", "Ruma", "Alamgir", "Jesmin", "Parvez"]
LAST = ["Akter", "Hossain", "Begum", "Mia", "Khatun", "Uddin", "Islam", "Rahman", "Sarker", "Das"]
COMPANIES = ["Sunrise Apparels Ltd.", "Greenline Garments", "Padma Knitwear Ltd.", "Meghna Fashions", "Shapla Textiles", "Orchid Apparel Co."]
LENDERS = ["Shanti Mohila Samity", "Uttoron Savings Group", "Alo Microfinance", "Jagoron Samity"]
UTILITIES = ["Palli Bidyut Samity", "Rupali Power Supply", "Jonota Bidyut Office"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

TIERS = {  # camera quality tiers
    "good": dict(blur=(0.3, 0.6), noise=(1.5, 3.0), jpeg=(88, 94), light=0.08, dark=(0.95, 1.0)),
    "medium": dict(blur=(0.7, 1.1), noise=(3.0, 5.0), jpeg=(78, 88), light=0.15, dark=(0.88, 1.0)),
    "poor": dict(blur=(1.2, 1.7), noise=(5.0, 8.0), jpeg=(65, 78), light=0.25, dark=(0.7, 0.9)),
    "unreadable": dict(blur=(3.5, 5.0), noise=(8.0, 12.0), jpeg=(45, 60), light=0.3, dark=(0.45, 0.7)),
}
EDIT_TYPES = {"payslip": ["inconsistent", "consistent", "identity"], "loan": ["inconsistent", "identity"], "bill": ["inconsistent", "consistent", "identity"]}


def font(family: str, size: int):
    k = (family, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(str(FONT_DIR / FONTS[family]), size)
    return _font_cache[k]


@dataclass
class Truth:
    doc_type: str
    family: str
    fields: dict = field(default_factory=dict)
    boxes: dict = field(default_factory=dict)   # field -> [x0, y0, x1, y1] in CURRENT image coordinates
    meta: dict = field(default_factory=dict)    # field -> font family/size/ink/dy


def _name(rng):
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def _fmt(v, dec=0):
    return f"{v:,.{dec}f}"


def _rows(doc_type, rng):
    """Return (title, header, rows) where rows are ('sep',) or (label, key, value, text)."""
    if doc_type == "payslip":
        basic = rng.randrange(8000, 20001, 250)
        house, med, trans, food = basic // 2, 750, 450, 1250
        hours = rng.randint(10, 80)
        rate = round(basic / 208 * 2, 2)
        ot = round(rate * hours)
        ded = rng.randrange(300, 1501, 50)
        net = basic + house + med + trans + food + ot - ded
        name, eid, month = _name(rng), f"SW-{rng.randint(1000, 9999)}", f"{rng.choice(MONTHS)} 2026"
        return rng.choice(COMPANIES), "Pay Slip", [
            ("Name", "name", name, name), ("ID / Grade", "emp_id", eid, eid), ("Month", "month", month, month), ("sep",),
            ("Basic", "basic", basic, _fmt(basic)), ("House rent", "house", house, _fmt(house)), ("Medical", "medical", med, _fmt(med)),
            ("Transport", "transport", trans, _fmt(trans)), ("Food", "food", food, _fmt(food)), ("sep",),
            ("OT hours", "ot_hours", hours, str(hours)), ("OT rate", "ot_rate", rate, _fmt(rate, 2)), ("OT amount", "ot_amount", ot, _fmt(ot)), ("sep",),
            ("Advance (deduction)", "deduction", ded, f"({_fmt(ded)})"), ("NET PAY", "net", net, _fmt(net))]
    if doc_type == "loan":
        principal = rng.randrange(10000, 100001, 1000)
        flat, months = rng.choice([10, 12, 15, 18, 20]), rng.choice([6, 12, 18, 24])
        exact = principal * (1 + flat / 100 * months / 12)
        inst = round(exact / months)
        total = inst * months
        member, group = _name(rng), f"Ward {rng.randint(1, 9)} / {rng.randint(1, 20):02d}"
        date = f"{rng.randint(1, 28):02d} {rng.choice(MONTHS)[:3]} 2026"
        return rng.choice(LENDERS), "Loan Agreement Slip", [
            ("Member", "member", member, member), ("Group / Center", "group", group, group), ("sep",),
            ("Loan amount", "principal", principal, _fmt(principal)), ("Service charge (flat)", "flat", flat, f"{flat}% p.a."),
            ("Term", "months", months, f"{months} months"), ("sep",),
            ("Installment", "inst", inst, f"{_fmt(inst)} / month"), ("Total payable", "total", total, _fmt(total)), ("First installment", "date", date, date)]
    slabs = load_pack("bill")["params"]["slabs"]
    units = rng.randint(80, 600)
    left, energy = units, 0.0
    for s in slabs:
        used = min(left, s["units"] if s["units"] is not None else 10 ** 9)
        energy += used * s["rate"]
        left -= used
        if left <= 0:
            break
    energy = round(energy, 2)
    demand = float(rng.choice([42, 84, 126]))
    vat = round((energy + demand) * 0.05, 2)
    misc = 0.0
    total = round(energy + demand + vat + misc, 2)
    cons, meter = _name(rng), f"{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}-{rng.randint(10, 99)}"
    return rng.choice(UTILITIES), "Electricity Bill", [
        ("Consumer", "consumer", cons, cons), ("Meter no.", "meter", meter, meter), ("sep",),
        ("Units consumed", "units", units, str(units)), ("Energy charge", "energy", energy, _fmt(energy, 2)),
        ("Demand charge", "demand", demand, _fmt(demand, 2)), ("VAT 5%", "vat", vat, _fmt(vat, 2)),
        ("Adjustment / other", "misc", misc, _fmt(misc, 2)), ("sep",), ("TOTAL PAYABLE", "total", total, _fmt(total, 2))]


def render(doc_type: str, rng: random.Random, nrng: np.random.Generator, family: str | None = None):
    family = family or rng.choice(list(FONTS))
    size = rng.choice([20, 22, 24])
    paper = rng.choice([(255, 253, 246), (250, 250, 250), (248, 245, 235), (252, 250, 240)])
    ink = rng.choice([(30, 30, 28), (20, 20, 40), (40, 30, 30)])
    arr = np.clip(np.array(paper, np.float32) + nrng.normal(0, 2.2, (H, W, 3)), 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    company, title, rows = _rows(doc_type, rng)
    accent = rng.choice([(13, 74, 55), (30, 60, 120), (120, 40, 40)])
    d.rectangle([40, 40, 76, 76], fill=accent)
    d.ellipse([52, 52, 64, 64], fill=paper)
    d.text((92, 38), company, font=font(family, 30), fill=ink)
    d.text((92, 78), f"{title}  ·  2026", font=font(family, 18), fill=(110, 105, 90))
    d.line([40, 120, W - 40, 120], fill=ink, width=2)
    truth = Truth(doc_type, family)
    f = font(family, size)
    y, row_h = 150, rng.randint(36, 44)
    for r in rows:
        if r[0] == "sep":
            d.line([40, y + 6, W - 40, y + 6], fill=(190, 184, 165), width=1)
            y += 18
            continue
        label, key, value, text = r
        d.text((48, y), label, font=f, fill=ink)
        right = W - 48
        d.text((right, y), text, font=f, fill=ink, anchor="ra")
        b = d.textbbox((right, y), text, font=f, anchor="ra")
        truth.fields[key] = value
        truth.boxes[key] = [float(b[0]), float(b[1]), float(b[2]), float(b[3])]
        truth.meta[key] = dict(family=family, size=size, ink=ink, dy=b[1] - y)
        y += row_h
    # decoration a forger might copy: stamp + signature line
    sx, sy = rng.randint(380, 520), min(y + 30, H - 170)
    d.ellipse([sx, sy, sx + 120, sy + 120], outline=(180, 40, 40), width=3)
    d.text((sx + 60, sy + 60), "PAID", font=font("sans", 24), fill=(180, 40, 40), anchor="mm")
    d.line([60, sy + 100, 280, sy + 100], fill=ink, width=1)
    d.text((60, sy + 106), "Authorised signature", font=font(family, 14), fill=(110, 105, 90))
    return np.array(img), truth


# ------------------------------------------------------------------ tampering
def _plan(truth: Truth, edit_type: str, rng: random.Random):
    """Return a list of (field, new_value, new_text)."""
    f, t = truth.fields, truth.doc_type
    plan = []
    if edit_type == "inconsistent":
        key = {"payslip": "net", "loan": "total", "bill": "total"}[t]
        old = f[key]
        factor = rng.choice([rng.uniform(0.6, 0.93), rng.uniform(1.07, 1.4)])
        new = round(old * factor, 2 if t == "bill" else 0)
        new = int(new) if t != "bill" else new
        plan.append((key, new, _fmt(new, 2) if t == "bill" else _fmt(new)))
    elif edit_type == "consistent":
        if t == "payslip":
            ded = f["deduction"]
            nd = max(0, ded - int(rng.uniform(150, ded * 0.8)))
            plan += [("deduction", nd, f"({_fmt(nd)})"), ("net", f["net"] + (ded - nd), _fmt(f["net"] + ded - nd))]
        else:  # bill: add an unexplained adjustment and keep the total arithmetic consistent
            nm = round(f["misc"] + rng.uniform(100, 600), 2)
            nt = round(f["total"] + (nm - f["misc"]), 2)
            plan += [("misc", nm, _fmt(nm, 2)), ("total", nt, _fmt(nt, 2))]
    else:  # identity: arithmetic untouched
        key = {"payslip": rng.choice(["name", "emp_id"]), "loan": rng.choice(["member", "group"]), "bill": rng.choice(["consumer", "meter"])}[t]
        old = str(f[key])
        if key in ("name", "member", "consumer"):
            new = _name(rng)
        elif key == "emp_id":
            new = f"SW-{rng.randint(1000, 9999)}"
        elif key == "meter":
            new = f"{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}-{rng.randint(10, 99)}"
        else:
            new = f"Ward {rng.randint(1, 9)} / {rng.randint(1, 20):02d}"
        plan.append((key, new, new))
    return plan


def _paint(arr, truth, key, text, difficulty, rng, nrng, blur):
    m = truth.meta[key]
    x0, y0, x1, y1 = [int(round(v)) for v in truth.boxes[key]]
    fam, size, ink = m["family"], m["size"], m["ink"]
    shift = 0
    if difficulty == "easy":
        fam = rng.choice([x for x in FONTS if x != fam])
        size += rng.choice([-4, -3, 3, 4])
        ink = tuple(int(np.clip(c + rng.choice([-30, 30]), 0, 255)) for c in ink)
        shift = rng.randint(-3, 3)
    elif difficulty == "medium":
        size += rng.choice([-1, 0, 1])
        shift = rng.randint(-2, 2)
        ink = tuple(int(np.clip(c + rng.randint(-8, 8), 0, 255)) for c in ink)
    else:
        shift = rng.randint(-1, 1)
    f = font(fam, size)
    right, ytop = x1 + shift, y0 - m["dy"]
    nb = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((right, ytop), text, font=f, anchor="ra")
    fx0, fy0 = max(0, min(x0, nb[0]) - 3), max(0, min(y0, nb[1]) - 3)
    fx1, fy1 = min(arr.shape[1], max(x1, nb[2]) + 3), min(arr.shape[0], max(y1, nb[3]) + 3)
    ref = arr[max(0, y0):y1, 330:420].reshape(-1, 3).astype(np.float32)
    mean, std = ref.mean(0), ref.std(0)
    shape = (fy1 - fy0, fx1 - fx0, 3)
    fill = np.tile(mean, (shape[0], shape[1], 1)) if difficulty == "easy" else mean + nrng.normal(0, 1, shape) * std
    pil = Image.fromarray(np.clip(fill, 0, 255).astype(np.uint8))
    ImageDraw.Draw(pil).text((right - fx0, ytop - fy0), text, font=f, fill=ink, anchor="ra")
    reg = np.array(pil)
    if difficulty == "hard" and blur > 0.2:
        reg = cv2.GaussianBlur(reg, (0, 0), blur * 0.8)
    arr[fy0:fy1, fx0:fx1] = reg
    truth.boxes[key] = [float(min(x0, nb[0])), float(min(y0, nb[1])), float(max(x1, nb[2])), float(max(y1, nb[3]))]
    return [float(fx0), float(fy0), float(fx1), float(fy1)]


def apply_tamper(arr, truth, edit_type, difficulty, rng, nrng, blur=0.0):
    edited = []
    for key, val, text in _plan(truth, edit_type, rng):
        box = _paint(arr, truth, key, text, difficulty, rng, nrng, blur)
        truth.fields[key] = val
        edited.append({"field": key, "box": box})
    return arr, edited


# ------------------------------------------------------------------ phone camera
def _map_box(box, M):
    x0, y0, x1, y1 = box
    pts = np.array([[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]], np.float32)
    o = cv2.perspectiveTransform(pts, M)[0]
    return [float(o[:, 0].min()), float(o[:, 1].min()), float(o[:, 0].max()), float(o[:, 1].max())]


def camera(arr, tier, rng, nrng):
    t = TIERS[tier]
    jit = lambda s: rng.uniform(-s, s)
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    k = 10 if tier != "good" else 6
    dst = np.float32([[jit(k) + 6, jit(k) + 6], [W + jit(k) - 6, jit(k) + 6], [W + jit(k) - 6, H + jit(k) - 6], [jit(k) + 6, H + jit(k) - 6]])
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(arr, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(125, 105, 85))
    gx, gy = np.linspace(-0.5, 0.5, W)[None, :], np.linspace(-0.5, 0.5, H)[:, None]
    light = 1 + rng.uniform(-t["light"], t["light"]) * gx + rng.uniform(-t["light"], t["light"]) * gy
    out = out.astype(np.float32) * light[..., None] * rng.uniform(*t["dark"])
    sigma = rng.uniform(*t["blur"])
    out = cv2.GaussianBlur(out, (0, 0), sigma)
    out = out + nrng.normal(0, rng.uniform(*t["noise"]), out.shape)
    return np.clip(out, 0, 255).astype(np.uint8), M, sigma


def jpeg_bytes(arr, q):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "JPEG", quality=int(q))
    return buf.getvalue()


def jpeg_roundtrip(arr, q):
    return np.array(Image.open(io.BytesIO(jpeg_bytes(arr, q))).convert("RGB"))


@dataclass
class Sample:
    jpeg: bytes
    doc_type: str
    tampered: bool
    edit_type: str | None
    difficulty: str | None
    scenario: str | None
    tier: str
    family: str
    fields: dict
    tamper_boxes: list


def make_sample(doc_type, seed, tampered=False, edit_type=None, difficulty=None, scenario="post", tier="good", family=None, camera_seed=None) -> Sample:
    rng, nrng = random.Random(seed), np.random.default_rng(seed)
    arr, truth = render(doc_type, rng, nrng, family)
    edits = []
    if tampered and scenario == "pre":
        arr, edits = apply_tamper(arr, truth, edit_type, difficulty, rng, nrng, 0.0)
    if camera_seed is not None:   # same document, photographed again with a different camera/lighting
        rng, nrng = random.Random(camera_seed), np.random.default_rng(camera_seed)
    photo, M, sigma = camera(arr, tier, rng, nrng)
    if tampered and scenario == "pre":
        for e in edits:
            e["box"] = _map_box(e["box"], M)
    else:
        truth.boxes = {k: _map_box(b, M) for k, b in truth.boxes.items()}
    t = TIERS[tier]
    photo = jpeg_roundtrip(photo, rng.randint(*t["jpeg"]))                       # q1: the "camera" save
    if tampered and scenario == "post":
        photo, edits = apply_tamper(photo, truth, edit_type, difficulty, rng, nrng, sigma)
    final = jpeg_bytes(photo, rng.randint(*t["jpeg"]) - 5)                       # q2: whole-image save, same for every sample
    return Sample(final, doc_type, tampered, edit_type if tampered else None, difficulty if tampered else None,
                  scenario if tampered else None, tier, truth.family, dict(truth.fields), [e["box"] for e in edits])
