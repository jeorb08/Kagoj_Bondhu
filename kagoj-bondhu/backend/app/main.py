"""Kagoj Bondhu API.

  GET  /api/health        liveness + whether live extraction is configured
  GET  /api/rules         rule-pack parameters (single source of truth for numbers like 208 or 24%)
  POST /api/read          photo -> structured fields (vision model)      [AI reads]
  POST /api/check         confirmed values -> findings (rules engine)    [code checks]

Privacy: images and values are processed in memory; optional extraction cache is opt-in. Provider processing has separate terms.
"""
import os
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import extract, explain, speech, proof, comparison
from .ai_client import AIUnavailable, public_error
from .rules import all_params, check
from .samples import SAMPLES
from .rules import load_pack
from .verify import service
import json
import base64

Module = Literal["payslip", "loan", "bill", "khata"]

app = FastAPI(title="Kagoj Bondhu", version="1.1.0")

_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"], allow_headers=["*"])

_hits: dict = defaultdict(list)


def _rate_limit(ip: str) -> None:
    limit = int(os.getenv("RATE_LIMIT_PER_HOUR", "40"))
    now = time.time()
    _hits[ip] = [t for t in _hits[ip] if now - t < 3600]
    if len(_hits[ip]) >= limit:
        raise HTTPException(429, "Too many photos for now. Please try again later.")
    _hits[ip].append(now)


def _live() -> bool:
    p = extract.provider()
    return (p == "gemini" and bool(os.getenv("GEMINI_API_KEY")) and bool(os.getenv("GEMINI_MODEL"))) or (p == "anthropic" and bool(os.getenv("ANTHROPIC_API_KEY")) and bool(os.getenv("MODEL")))


class ReadRequest(BaseModel):
    module: Module
    image: str  # data URL, already compressed by the browser


class CheckRequest(BaseModel):
    module: Module
    values: dict[str, Any]
    as_of: Optional[date] = None
    explain_ai: bool = True


@app.get("/api/health")
def health():
    return {"ok": True, "build": "photo-recovery-v2", "verify_model": service.MODEL.exists(), "extraction": "live" if _live() else "mock" if os.getenv("MOCK_EXTRACTION", "0") == "1" or os.getenv("PROVIDER", "") == "mock" else "not_configured", "provider": extract.provider(), "explanation_enabled": os.getenv("AI_EXPLANATIONS", "1") == "1", "cloud_speech": speech.configured(), "model": os.getenv("GEMINI_MODEL", "") if extract.provider()=="gemini" else os.getenv("MODEL", "")}


@app.get("/api/rules")
def rules():
    return all_params()


@app.post("/api/read")
def read(req: ReadRequest, request: Request):
    _rate_limit(request.client.host if request.client else "unknown")
    try:
        service.decode_image(req.image)
    except extract.BadImage as e:
        raise HTTPException(400, str(e))
    if not _live():
        if os.getenv("MOCK_EXTRACTION", "0") == "1" or os.getenv("PROVIDER", "") == "mock":
            return {"mode": "mock", "module": req.module, **SAMPLES[req.module]}
        raise HTTPException(503, "Set the vision provider API key and model in .env, or choose a sample explicitly.")
    try:
        return extract.read_document(req.module, req.image)
    except extract.BadImage as e:
        raise HTTPException(400, str(e))
    except extract.RateLimited:
        raise HTTPException(429, "Reading quota is busy right now. Retry later.")
    except extract.NotConfigured as e:
        raise HTTPException(503, str(e))
    except AIUnavailable as e:
        raise HTTPException(429 if e.reason == "quota_busy" else 502, public_error(e))
    except Exception:
        # Deliberately generic: never echo model or image details back.
        raise HTTPException(502, "Could not read this photo. Try again with a clearer, flatter picture.")


@app.post("/api/check")
def do_check(req: CheckRequest, request: Request):
    if req.explain_ai:
        _rate_limit(request.client.host if request.client else 'unknown')
    try:
        result = check(req.module, req.values, req.as_of)
        out = {"module": req.module, "result": result,
               "rule": {"id": req.module, "version": load_pack(req.module)["version"], "source": load_pack(req.module)["source"]}}
        out['proof'] = proof.build(req.module, req.values, result)
        if req.explain_ai:
            out['explanation'] = explain.explain(explain.borrower_evidence(req.module, result, req.values))
        return out
    except (KeyError, ValueError, TypeError, OverflowError) as e:
        raise HTTPException(422, str(e))


class VerifyRequest(BaseModel):
    module: Literal['payslip', 'loan', 'bill']
    image: str
    values: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False
    reference_image: Optional[str] = None
    reference_values: Optional[dict[str, Any]] = None
    explain_ai: bool = True

@app.post('/api/verify')
def verify(req: VerifyRequest, request: Request):
    _rate_limit(request.client.host if request.client else 'unknown')
    try:
        result = service.verify(req.module, req.image, req.values, req.confirmed,
                              req.reference_image, req.reference_values)
        if req.explain_ai:
            result["explanation"] = explain.explain(explain.verify_evidence(result))
        return result
    except extract.BadImage as e:
        raise HTTPException(400, str(e))
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(422, str(e))

class VerifyReadRequest(BaseModel):
    module: Literal['payslip','loan','bill','application']
    image: str

@app.post('/api/verify/read')
def verify_read(req: VerifyReadRequest, request: Request):
    _rate_limit(request.client.host if request.client else 'unknown')
    try:
        rgb = service.decode_image(req.image)
        q = service.F.quality(rgb)
        a = service.artifact()
        threshold = a['quality_threshold'] if a else 109.0
        if min(q['width'],q['height']) < 320 or q['edge_strength'] < threshold:
            return {'mode':'cannot_assess','module':req.module,'fields':{}, 'quality':q,
                    'message':'Photo is too unclear for reliable reading. Please retake it.'}
        if not _live():
            raise HTTPException(503, 'Configure the vision provider API key and model in .env; no sample fields were substituted.')
        result = extract.read_document(req.module, req.image, scope='verify')
        return {**result, 'quality':q}
    except HTTPException:
        raise
    except extract.BadImage as e:
        raise HTTPException(400, str(e))
    except extract.RateLimited:
        raise HTTPException(429, 'Vision-model quota is busy. Retry later or enter fields manually.')
    except extract.NotConfigured as e:
        raise HTTPException(503, str(e))
    except AIUnavailable as e:
        raise HTTPException(429 if e.reason == "quota_busy" else 502, public_error(e))
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, 'The reader returned malformed fields; retry or enter them manually.')
    except Exception:
        raise HTTPException(502, 'Could not read this image. Retry or enter the printed fields manually.')

class ComparisonDocument(BaseModel):
    kind: Literal['payslip','application']
    values: dict[str, Any]
    confirmed: bool = False

class CompareRequest(BaseModel):
    left: ComparisonDocument
    right: ComparisonDocument

@app.post('/api/verify/compare')
def compare_documents(req: CompareRequest, request: Request):
    _rate_limit(request.client.host if request.client else 'unknown')
    try:
        return comparison.compare(req.left.model_dump(), req.right.model_dump())
    except (ValueError, TypeError, OverflowError) as e:
        raise HTTPException(422, str(e))

class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: Literal['bn','en'] = 'bn'

@app.post('/api/speak')
def speak(req: SpeakRequest, request: Request):
    _rate_limit(request.client.host if request.client else 'unknown')
    try:
        audio, media = speech.synthesize(req.text,req.language)
        return Response(content=audio,media_type=media,headers={'Cache-Control':'no-store'})
    except AIUnavailable as e:
        raise HTTPException(503 if e.reason.endswith('not_configured') else 502,public_error(e))
    except ValueError as e:
        raise HTTPException(422,str(e))

@app.get('/api/verify/samples')
def verify_samples():
    path = Path(__file__).resolve().parents[2] / 'demo' / 'manifest.json'
    return json.loads(path.read_text()) if path.exists() else []

@app.get('/api/verify/sample/{sample_id}')
def verify_sample(sample_id: str):
    root = Path(__file__).resolve().parents[2] / 'demo'
    manifest = verify_samples()
    entry = next((x for x in manifest if x['id'] == sample_id), None)
    if entry is None:
        raise HTTPException(404, 'Sample not found')
    data = (root / (sample_id + '.jpg')).read_bytes()
    return {**entry, 'image': 'data:image/jpeg;base64,' + base64.b64encode(data).decode()}

@app.middleware('http')
async def security_headers(request: Request, call_next):
    if len(request.headers.get('content-length', '0')) > 12 or not request.headers.get('content-length', '0').isdigit() or int(request.headers.get('content-length', '0')) > 18 * 1024 * 1024:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Request is too large'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api/') else 'no-cache'
    return response


_frontend = Path(__file__).resolve().parents[2] / "frontend"
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
