"""Layer 4: reuse detection. Has this same document image been submitted before (maybe re-photographed, cropped
or with a changed name)?  Perceptual hash for near-identical files + ORB keypoints with a RANSAC homography for
re-photographed / cropped / rotated copies.  Only compact descriptors are kept in memory, never the images."""
from __future__ import annotations

import cv2
import numpy as np

_orb = cv2.ORB_create(nfeatures=700)
_bf = cv2.BFMatcher(cv2.NORM_HAMMING)


def signature(rgb: np.ndarray) -> dict:
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, (720, int(720 * g.shape[0] / g.shape[1])), interpolation=cv2.INTER_AREA)
    small = cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(small)[:8, :8]
    bits = (dct.ravel() > np.median(dct.ravel()[1:])).astype(np.uint8)
    kp, des = _orb.detectAndCompute(g, None)
    pts = np.array([k.pt for k in kp], np.float32) if kp else np.zeros((0, 2), np.float32)
    return {"phash": bits, "des": des, "pts": pts}


def hamming(a, b) -> int:
    return int((a["phash"] != b["phash"]).sum())


def orb_inliers(a, b, ratio=0.75) -> int:
    if a["des"] is None or b["des"] is None or len(a["des"]) < 8 or len(b["des"]) < 8:
        return 0
    good = []
    for pair in _bf.knnMatch(a["des"], b["des"], k=2):
        if len(pair) == 2 and pair[0].distance < ratio * pair[1].distance:
            good.append(pair[0])
    if len(good) < 8:
        return len(good) if len(good) < 4 else 0
    src = a["pts"][[m.queryIdx for m in good]].reshape(-1, 1, 2)
    dst = b["pts"][[m.trainIdx for m in good]].reshape(-1, 1, 2)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(mask.sum()) if mask is not None else 0


def similarity(a, b) -> dict:
    return {"hamming": hamming(a, b), "inliers": orb_inliers(a, b)}


class DuplicateIndex:
    """In-memory case index. Replace with a database or vector index in production."""

    def __init__(self, inlier_threshold: int = 60, max_hamming: int = 10):
        self.items: list = []
        self.inlier_threshold, self.max_hamming = inlier_threshold, max_hamming

    def query(self, sig):
        best = None
        for case_id, other in self.items:
            s = similarity(sig, other)
            if s["hamming"] <= self.max_hamming or s["inliers"] >= self.inlier_threshold:
                if best is None or s["inliers"] > best["inliers"]:
                    best = {"case_id": case_id, **s}
        return best

    def add(self, case_id, sig):
        self.items.append((case_id, sig))
        if len(self.items) > 500:
            self.items.pop(0)
