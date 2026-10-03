"""Patch-level forensic features. A patch is 32x32 px. Tampering shows up as INCONSISTENCY, so every feature is
also normalised against the rest of the same image (robust z-score over text-bearing patches)."""
from __future__ import annotations

import cv2
import numpy as np

P = 32
RAW = ["ela90_mean", "ela90_std", "ela75_mean", "ela75_p95", "noise_std", "noise_abs", "lap_var", "block", "gray_mean", "gray_std", "edge"]
Z_OF = ["ela90_mean", "ela90_std", "ela75_mean", "ela75_p95", "noise_std", "noise_abs", "lap_var", "block"]
NAMES = RAW + [f"z_{n}" for n in Z_OF]


def decode(jpeg_or_rgb) -> np.ndarray:
    if isinstance(jpeg_or_rgb, (bytes, bytearray)):
        a = cv2.imdecode(np.frombuffer(jpeg_or_rgb, np.uint8), cv2.IMREAD_COLOR)
        return cv2.cvtColor(a, cv2.COLOR_BGR2RGB)
    return jpeg_or_rgb


def _blocks(x, gh, gw):
    return x[: gh * P, : gw * P].reshape(gh, P, gw, P).transpose(0, 2, 1, 3).reshape(gh, gw, P * P)


def _ela(bgr, q):
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, q])
    rec = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return np.abs(bgr.astype(np.int16) - rec.astype(np.int16)).mean(2).astype(np.float32)


def _block_ratio(gf, gh, gw):
    """JPEG blockiness: neighbour-difference energy at 8px block boundaries vs inside blocks (per patch)."""
    mask = (np.arange(P) % 8 == 7)
    res = []
    for axis in (1, 0):
        d = np.abs(gf[:, 1:] - gf[:, :-1]) if axis == 1 else np.abs(gf[1:, :] - gf[:-1, :])
        d = np.pad(d, ((0, 0), (0, 1)) if axis == 1 else ((0, 1), (0, 0)))
        blk = _blocks(d, gh, gw).reshape(gh, gw, P, P)
        sel = blk[..., :, mask] if axis == 1 else blk[..., mask, :]
        oth = blk[..., :, ~mask] if axis == 1 else blk[..., ~mask, :]
        res.append((sel.mean((-1, -2)) + 1.0) / (oth.mean((-1, -2)) + 1.0))
    return (res[0] + res[1]) / 2


def patch_features(rgb: np.ndarray):
    """Returns (features [gh*gw, F], (gh, gw))."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    H, W = g.shape
    gh, gw = H // P, W // P
    gf = g.astype(np.float32)
    e90, e75 = _ela(bgr, 90), _ela(bgr, 75)
    resid = gf - cv2.medianBlur(g, 3).astype(np.float32)
    lap = cv2.Laplacian(gf, cv2.CV_32F)
    edges = (cv2.Canny(g, 60, 140) > 0).astype(np.float32)
    B = lambda x: _blocks(x, gh, gw)
    f = {
        "ela90_mean": B(e90).mean(-1), "ela90_std": B(e90).std(-1), "ela75_mean": B(e75).mean(-1),
        "ela75_p95": np.percentile(B(e75), 95, axis=-1), "noise_std": B(resid).std(-1), "noise_abs": np.abs(B(resid)).mean(-1),
        "lap_var": np.log1p(B(lap).var(-1)), "block": _block_ratio(gf, gh, gw),
        "gray_mean": B(gf).mean(-1), "gray_std": B(gf).std(-1), "edge": B(edges).mean(-1),
    }
    text = (f["edge"] > 0.01) | (f["gray_std"] > 10)
    if text.sum() < 8:
        text = np.ones_like(text, bool)
    cols = [f[n].ravel() for n in RAW]
    for n in Z_OF:
        ref = f[n][text]
        med = np.median(ref)
        mad = np.median(np.abs(ref - med)) * 1.4826 + 1e-3
        cols.append(((f[n] - med) / mad).ravel())
    return np.stack(cols, 1).astype(np.float32), (gh, gw)


def patch_labels(shape, boxes, min_overlap=0.15):
    gh, gw = shape
    y = np.zeros((gh, gw), np.int8)
    for x0, y0, x1, y1 in boxes:
        for r in range(gh):
            for c in range(gw):
                px0, py0 = c * P, r * P
                iw = min(px0 + P, x1) - max(px0, x0)
                ih = min(py0 + P, y1) - max(py0, y0)
                if iw > 0 and ih > 0 and iw * ih / (P * P) >= min_overlap:
                    y[r, c] = 1
    return y.ravel()


def image_score(patch_prob: np.ndarray, k=3) -> float:
    return float(np.sort(patch_prob)[-k:].mean())


# ---------- image quality gate ("Cannot assess") ----------
def quality(rgb: np.ndarray) -> dict:
    """edge_strength = 99.5th percentile of gradient magnitude after light denoising, on a 720px-wide copy.
    It measures how crisp the text edges are and, unlike a raw Laplacian, is not fooled by camera noise."""
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    small = cv2.resize(g, (720, int(720 * g.shape[0] / g.shape[1])), interpolation=cv2.INTER_AREA).astype(np.float32)
    d = cv2.GaussianBlur(small, (0, 0), 1.2)
    mag = np.hypot(cv2.Sobel(d, cv2.CV_32F, 1, 0), cv2.Sobel(d, cv2.CV_32F, 0, 1))
    return {"edge_strength": round(float(np.percentile(mag, 99.5)), 1), "brightness": round(float(g.mean()), 1),
            "width": int(g.shape[1]), "height": int(g.shape[0])}
