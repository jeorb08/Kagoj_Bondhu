"""Sample extraction results, used in MOCK mode (no API key, offline demo, or as a safety net)."""

SAMPLES = {
    "payslip": {"fields": {
        "basic": {"value": 8000, "confidence": 0.99},
        "otHours": {"value": 60, "confidence": 0.87},
        "otPaid": {"value": 3000, "confidence": 0.95}}},
    "loan": {"fields": {
        "principal": {"value": 30000, "confidence": 0.99},
        "flat": {"value": 15, "confidence": 0.96},
        "months": {"value": 12, "confidence": 0.98},
        "inst": {"value": 2875, "confidence": 0.93}}},
    "bill": {"fields": {
        "units": {"value": 320, "confidence": 0.97},
        "demand": {"value": 84, "confidence": 0.95},
        "misc": {"value": 450, "confidence": 0.82},
        "total": {"value": 2862.8, "confidence": 0.96}}},
    "khata": {"entries": [
        {"date": "2026-07-03", "name": "Karim", "amount": 1200, "kind": "credit", "confidence": 0.98},
        {"date": "2026-07-19", "name": "Nasima", "amount": 3100, "kind": "credit", "confidence": 0.96},
        {"date": "2026-08-12", "name": "Karim", "amount": 1500, "kind": "credit", "confidence": 0.71},
        {"date": "2026-08-15", "name": "Rahima", "amount": 850, "kind": "credit", "confidence": 0.94},
        {"date": "2026-08-20", "name": "Salam", "amount": 2300, "kind": "credit", "confidence": 0.97},
        {"date": "2026-09-02", "name": "Salam", "amount": 500, "kind": "payment", "confidence": 0.95},
        {"date": "2026-09-10", "name": "Jamal", "amount": 640, "kind": "credit", "confidence": 0.93},
        {"date": "2026-09-20", "name": "Karim", "amount": 1500, "kind": "credit", "confidence": 0.97}]},
}
