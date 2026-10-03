"""Evidence-based triage. No automatic lending decisions or persistent case index."""
import base64
import io
import math
from functools import lru_cache
from pathlib import Path

import cv2
import joblib
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..extract import parse_data_url, BadImage
from . import consistency, features as F, duplicates

MODEL = Path(__file__).resolve().parents[2] / 'models' / 'tamper_v2.joblib'
REQUIRED = {
    'payslip': ['basic', 'house', 'medical', 'transport', 'food', 'ot_amount', 'deduction', 'net'],
    'loan': ['principal', 'flat', 'months', 'inst', 'total'],
    'bill': ['units', 'energy', 'demand', 'vat', 'misc', 'total'],
}

@lru_cache(maxsize=1)
def artifact():
    # Only the model generated locally by ml/train_final.py, never a user-supplied pickle.
    return joblib.load(MODEL) if MODEL.exists() else None


def decode_image(data_url):
    _, data = parse_data_url(data_url)
    try:
        with Image.open(io.BytesIO(base64.b64decode(data))) as im:
            if im.width * im.height > 16_000_000 or min(im.size) < 32:
                raise BadImage('Image dimensions outside supported range (32 px to 16 megapixels)')
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((1440, 1920))
            return np.asarray(im)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise BadImage('File is not a readable image')


def finding(code, en, bn, fields=None, category='consistency'):
    return dict(code=code, en=en, bn=bn, fields=fields or [], category=category, severity='review')


def infer(rgb):
    a = artifact()
    if a is None:
        return {'available': False, 'limitation': 'Model not trained; arithmetic and image quality only'}, []
    # Match training geometry. This changes no aspect ratio.
    h, w = rgb.shape[:2]
    resized = cv2.resize(rgb, (720, max(32, round(h * 720 / w))))
    x, (gh, gw) = F.patch_features(resized)
    probs = a['model'].predict_proba(x)[:, 1]
    score = F.image_score(probs)
    threshold = a['threshold']
    regions = []
    if score >= threshold:
        for idx in np.argsort(probs)[-3:][::-1]:
            r, c = divmod(int(idx), gw)
            regions.append({'x': c * F.P / resized.shape[1], 'y': r * F.P / resized.shape[0],
                            'width': F.P / resized.shape[1], 'height': F.P / resized.shape[0],
                            'score': round(float(probs[idx]), 4)})
    return {'available': True, 'version': a['version'], 'score': round(score, 4),
            'threshold': round(threshold, 4), 'flagged': score >= threshold,
            'meaning': 'Synthetic-trained anomaly score; NOT probability of forgery'}, regions


def verify(module, image, values, confirmed=False, reference_image=None, reference_values=None):
    rgb = decode_image(image)
    q = F.quality(rgb)
    a = artifact()
    threshold = a['quality_threshold'] if a else 109.0
    findings, missing, regions = [], [], []
    quality_bad = min(q['width'], q['height']) < 320 or q['edge_strength'] < threshold
    if quality_bad:
        findings.append(finding('quality.retake', 'Photo is too small, blank or unclear. Please retake it.',
            'ছবিটি ছোট, ফাঁকা বা অস্পষ্ট। আবার পরিষ্কার ছবি তুলুন।', category='quality'))
        ml = {'available': a is not None, 'assessed': False}
        outcome = 'cannot_assess'
    else:
        numeric = {}
        for k in REQUIRED[module] + (['ot_hours', 'ot_rate'] if module == 'payslip' else []):
            v = values.get(k)
            if v is None or v == '':
                if k in REQUIRED[module]: missing.append(k)
                continue
            try: n = float(v)
            except (ValueError, TypeError): raise ValueError(f'{k} must be numeric')
            if not math.isfinite(n) or n < 0 or n > 1e9: raise ValueError(f'{k} is outside supported range')
            numeric[k] = n
        if not confirmed:
            missing.append('human_confirmation')
        # No tariff law claims in Verify: compare printed bill components only.
        checks = consistency.check(module, numeric)
        checks = [f for f in checks if f['code'] not in ('bill.energy_mismatch', 'bill.unexplained_adjustment')]
        if confirmed:
            findings.extend({**f, 'category': 'consistency'} for f in checks)
        ml, regions = infer(rgb)
        if ml.get('flagged'):
            findings.append(finding('visual.anomaly', 'The model found unusual image patches. Inspect the marked regions; this is not proof of editing.',
                'মডেল ছবির কিছু অংশে অস্বাভাবিকতা পেয়েছে। চিহ্নিত অংশ দেখুন; এটি সম্পাদনার প্রমাণ নয়।', category='visual'))
        if reference_image:
            ref = decode_image(reference_image)
            sim = duplicates.similarity(duplicates.signature(rgb), duplicates.signature(ref))
            if sim['hamming'] <= 6 and sim['inliers'] >= 60:
                findings.append({**finding('reuse.candidate', 'Similar image structure to the supplied reference. Shared templates can also match; compare the actual fields.',
                    'দেওয়া নমুনার সঙ্গে ছবির গঠনে মিল আছে। একই ফর্মেও মিল হতে পারে; তথ্যগুলো মিলিয়ে দেখুন।', category='reuse'), 'evidence': sim})
        if reference_values and confirmed:
            for key in ('name', 'emp_id', 'meter'):
                left = str(values.get(key, '')).strip().casefold()
                right = str(reference_values.get(key, '')).strip().casefold()
                if left and right and left != right:
                    findings.append(finding('identity.' + key, f'Confirmed {key} differs from the supplied reference; spelling differences need human review.',
                        f'নিশ্চিত করা {key} নমুনার সঙ্গে মেলেনি; বানানের পার্থক্য মানুষকে যাচাই করতে হবে।', [key], 'cross_document'))
        outcome = 'cannot_assess' if missing else ('needs_review' if findings else 'looks_consistent')
    labels = {'cannot_assess': ('Cannot assess', 'যাচাই করা যাচ্ছে না'),
              'needs_review': ('Needs human review', 'মানুষের পর্যালোচনা প্রয়োজন'),
              'looks_consistent': ('Looks consistent', 'যাচাই করা তথ্যগুলো মিলছে')}
    en, bn = labels[outcome]
    # A deterministic narrative cannot introduce facts beyond its finding objects.
    summary = {'en': en + '. ' + ' '.join(f['en'] for f in findings),
               'bn': bn + '। ' + ' '.join(f['bn'] for f in findings)}
    return {'outcome': outcome, 'label': {'en': en, 'bn': bn}, 'findings': findings, 'missing': missing,
            'quality': q, 'ml': ml, 'regions': regions, 'summary': summary,
            'next_action': 'request_clear_copy' if outcome == 'cannot_assess' else 'review_evidence' if outcome == 'needs_review' else 'continue_manual_review',
            'reupload_draft': 'আপনার কাগজটি যাচাই করতে আরও পরিষ্কার একটি ছবি প্রয়োজন। চারটি কোণসহ ভালো আলোতে ছবি তুলে আবার দিন। ধন্যবাদ।',
            'scope': 'Arithmetic, limited image quality, optional pairwise reuse and synthetic-trained visual signals. No authenticity certification. No automatic approval or rejection.',
            'privacy': 'No server-side case retention. Reference images are compared only within this request.'}
