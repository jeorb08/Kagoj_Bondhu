# Kagoj Bondhu — কাগজ বন্ধু

**A paper friend that helps people understand the documents behind their money.**

Kagoj Bondhu reads financial document photos, lets users confirm extracted fields, checks calculations with Python, and explains findings in Bangla or English. Its additional **Verify** mode helps reviewers inspect document consistency and possible visual edit signals.

> **AI reads and explains. Code checks the numbers. People confirm fields and make decisions.**

This is a hackathon prototype using fictional documents and synthetic evaluation data. It does not certify document authenticity or make lending decisions.

## A simple story

Rina receives a payslip and wants to check her overtime payment. She uploads a photo, reviews the numbers read by AI, and corrects any mistakes. Python calculates the expected overtime under the selected rule pack. Kagoj Bondhu explains any difference, reads the explanation aloud when speech is available, and lets her open **Show me the proof** to see the inputs and calculation.

A reviewer can use the same project to inspect a document or compare two confirmed documents. Findings are evidence for a person to review, rather than a verdict about the borrower.

## Features

| Feature | What it does |
| --- | --- |
| **Payslip** | Compares calculated overtime payment with the confirmed payment on the slip. |
| **Loan** | Calculates monthly IRR and effective annual borrowing cost from a repayment schedule. |
| **Khata** | Calculates customer balances and overdue unpaid credit; payments settle the oldest credit first. |
| **Bill** | Recalculates an electricity bill using the included February 2024 historical tariff snapshot. |
| **Show me the proof** | Displays confirmed inputs, calculation steps, rule reference/version and limitations. |
| **Verify** | Checks image quality, internal arithmetic, optional reference-image similarity and local ML edit signals. |
| **Compare two documents** | Compares confirmed names, employee IDs, income months and comparable income amounts. |
| **Bangla / English** | Switches the main interface and borrower explanations between languages. Some technical evidence remains in English. |
| **Voice** | Uses configured Gemini speech or a suitable device/browser voice when available. |
| **Low-data mode** | Reduces interface effects; borrower photos are compressed on the device. Live AI still requires internet. |

### Context-aware comparison

Compare two payslips, or a payslip and a fictional application. Upload each image, review the AI-read fields, then confirm both documents.

Income differences are flagged for review only when the income months match and the amounts use comparable net-income bases. Different months, missing periods or gross-versus-net amounts receive context notes. Name matching uses simple normalization, not a trained identity-matching system.

### Verify outcomes

- **Looks consistent:** no flagged inconsistency in the completed checks.
- **Needs human review:** one or more findings need explanation.
- **Cannot assess:** image quality, missing fields or comparison context prevents a complete assessment.

Visual edit signals and similarity scores are not proof of forgery. Reference-image checking compares against an image supplied for the current check; there is no shared database of previous applicants.

## How it works

1. **Capture:** upload a document photo.
2. **Extract:** Gemini vision returns structured fields as JSON.
3. **Confirm:** the user checks and corrects extracted values.
4. **Check:** Python applies deterministic calculations from YAML rule packs.
5. **Explain:** Gemini writes an explanation from server-generated findings, with numerical safeguards.
6. **Speak:** cloud or device speech reads the explanation when configured and available.

Verify also uses OpenCV/Pillow for image quality, perceptual hashing and ORB for reference-image similarity, and a locally trained scikit-learn model for patch-level visual signals.

## Technology

| Component | Technology |
| --- | --- |
| Interface | HTML, CSS, JavaScript |
| API | Python, FastAPI, Uvicorn |
| Photo reading and explanations | Gemini API; optional Anthropic adapter |
| Rule checks | Python and YAML |
| Image processing | OpenCV, Pillow, NumPy |
| Local tamper classifier | scikit-learn, joblib |
| Speech | Gemini TTS or browser speech synthesis |

## Requirements

- Windows 10/11, macOS, or Linux.
- Python **3.12** and `pip` (the setup commands below create an isolated virtual environment).
- Internet access for Gemini reading, explanations, or cloud speech.
- A Gemini API key and access to a supported vision model for live document reading. The project can still be explored with its fictional demo data without a live AI key, but photo extraction and AI explanations require provider access.
- No GPU is required. The local image checks and tamper-signal model run on CPU; allow a few minutes for dependency installation.
- A modern browser. Microphone access is not required; voice playback uses cloud speech or a browser/device voice when available.

The exact Python package versions are listed in `requirements.txt`.

## Run locally in VS Code

Use **Python 3.12**. Open the application folder containing `run.py`, `requirements.txt`, `backend/` and `frontend/`. If the repository has an outer folder, open a terminal in the inner application folder first.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
code .env
```

Run the copy command only when `.env` does not already exist; preserve any working local configuration.

Set these values in **`.env`**:

```dotenv
PROVIDER=gemini
GEMINI_API_KEY=YOUR_API_KEY_HERE
GEMINI_MODEL=YOUR_AVAILABLE_VISION_MODEL_ID
GEMINI_EXPLAIN_MODEL=
AI_EXPLANATIONS=1
AI_TIMEOUT_SECONDS=60
TTS_PROVIDER=browser
GEMINI_TTS_MODEL=
MOCK_EXTRACTION=0
CACHE_EXTRACTION=0
PORT=8000
```

Save the file. To list models available to your key and select reading/optional speech models, run:

```powershell
.\.venv\Scripts\python.exe configure_ai.py
```

Choose a vision-capable Flash/Pro model. Model listings can include specialized models unsuitable for reading documents. Availability and quota depend on the account. Press Enter at the optional speech prompt to use device speech.

Test the reading service:

```powershell
.\.venv\Scripts\python.exe diagnose_ai.py
```

This checks a basic request and photo extraction using the bundled fictional payslip. It prints configuration paths and field counts, not your API key or extracted document contents. You can optionally supply a different fictional image path:

```powershell
.\.venv\Scripts\python.exe diagnose_ai.py "C:\samples\payslip.jpg"
```

Start the application:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open **http://127.0.0.1:8000**. Keep the terminal open. Restart the server after changing `.env`. A VS Code launch configuration is also included; select the virtual environment interpreter before using F5.

### Build

There is no separate compile or frontend build step. `run.py` starts the FastAPI application and serves the included frontend. Install the dependencies and configure `.env` as described above, then run `run.py` to launch it.

### Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your local credentials.
.venv/bin/python configure_ai.py
.venv/bin/python diagnose_ai.py
.venv/bin/python run.py
```

### Optional cloud speech

Run `configure_ai.py` and select an available TTS model, or set:

```dotenv
TTS_PROVIDER=gemini
GEMINI_TTS_MODEL=YOUR_AVAILABLE_TTS_MODEL_ID
GEMINI_TTS_VOICE=Kore
```

Cloud speech uses the Gemini key and provider quota. Device speech depends on installed voices; Bangla audio may be unavailable on some devices.

## Environment variables

Create `.env` beside `run.py` from `.env.example`. Keep secret values local and use placeholders in public documentation. The project reads these settings:

| Variable | Purpose | Example / guidance |
| --- | --- | --- |
| `PROVIDER` | Selects the AI provider adapter. | `gemini` |
| `GEMINI_API_KEY` | Authenticates requests to Gemini. | `YOUR_API_KEY_HERE` — never commit a real key. |
| `GEMINI_MODEL` | Vision-capable model used for document reading. | Set to an available model ID using `configure_ai.py`. |
| `GEMINI_EXPLAIN_MODEL` | Optional model for written explanations; blank uses the configured default behavior. | Leave blank or enter an available model ID. |
| `AI_EXPLANATIONS` | Enables or disables AI-written explanations. | `1` to enable. |
| `AI_TIMEOUT_SECONDS` | Maximum time allowed for an AI request. | `60` |
| `TTS_PROVIDER` | Speech provider. | `browser` or `gemini`. |
| `GEMINI_TTS_MODEL` | Optional Gemini text-to-speech model. | Leave blank for browser speech, or set an available TTS model ID. |
| `GEMINI_TTS_VOICE` | Optional Gemini speech voice. | `Kore` |
| `MOCK_EXTRACTION` | Enables mock extraction for development/testing. | `0` for normal operation. |
| `CACHE_EXTRACTION` | Enables in-process extraction caching. | `0` disables caching. |
| `PORT` | Local server port. | `8000` |

Optional settings may be omitted when unused. Do not put a real API key in `.env.example`, source code, screenshots, or a public issue. Restart the app after editing `.env`.

## Live deployment

**Live deployment URL: [Add the public judge-accessible deployment URL before submitting].**

No deployment URL was included with the project materials. Replace this placeholder with the working public URL once the app has been deployed. If the app is not deployed, judges can run it locally by following the setup instructions above.

## Demo and synthetic data

Sample buttons load explicitly labelled fictional fields. Uploaded photos use live AI extraction when configured; failed requests do not silently substitute sample numbers.

Synthetic documents serve three purposes:

- Demonstrate the user flow with known answers.
- Train the local tamper classifier on genuine and edited fictional images.
- Test calculations and model behavior against known labels.

**Gemini was not trained or fine-tuned on this dataset.** Only the local tamper model was trained for this project. The code package includes demo images and the trained artifact; the larger generation/evaluation dataset is separate.

## Tests

From the application folder:

```powershell
$env:PYTHONPATH="backend"
$env:OMP_NUM_THREADS="2"
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

For Linux/macOS:

```bash
OMP_NUM_THREADS=2 PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
```

The photo-recovery version passed **76 automated software tests**, covering rule calculations, extraction handling, comparison context, explanation safeguards, speech responses and provider-error recovery. UI interaction checks also exercised failed-read messages and retry behavior.

These are software correctness checks, with simulated provider responses where applicable. They do not establish live service availability, OCR accuracy or real-world tamper-detection performance.

## API overview

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Configuration and local-model status; does not make a live provider request. |
| `GET /api/rules` | Rule-pack parameters and references. |
| `POST /api/read` | Borrower document photo extraction. |
| `POST /api/check` | Calculate from confirmed fields; return results, proof and optional explanation. |
| `POST /api/verify/read` | Quality-gated field extraction for Verify and comparison. |
| `POST /api/verify` | Document screening and evidence report. |
| `POST /api/verify/compare` | Compare two human-confirmed field sets. |
| `POST /api/speak` | Return configured cloud speech as WAV audio. |

Interactive API documentation is available at **http://127.0.0.1:8000/docs** while the server runs.

## Troubleshooting

| Message | What to check |
| --- | --- |
| `not_configured` | Save credentials and model in `.env` beside `run.py`; restart. Editing `.env.example` does not configure the app. |
| `invalid_api_key` / HTTP 401 | Replace an invalid or revoked key in local `.env`. |
| `access_denied` / HTTP 403 | Check API permissions and account/API availability. |
| `model_not_available` / HTTP 404 | Select a supported model through `configure_ai.py`. |
| `quota_busy` / HTTP 429 | Wait for quota recovery or review account limits. |
| `provider_overloaded` / HTTP 503 | Automatic retries have failed. Retry later or test another available vision model. |
| `invalid_request_or_model` | The image/request format was rejected; use `diagnose_ai.py` to isolate the failure. |
| `request_timeout` | Retry or try a smaller photo; the request has a bounded timeout. |

The recovery adapter retries temporary server errors and can make one JSON-mode fallback when a structured-output request fails. It does not invent fields or guarantee availability during provider outages.

## Privacy and API keys

- Keep real keys only in local `.env` or a deployment secret manager.
- Commit `.env.example` with an empty key, never a working credential.
- Images are processed in memory; the app does not persist uploads by default.
- Optional extraction caching is disabled by default and uses process memory.
- Remote AI providers receive uploaded images or structured findings under their own terms. “No app storage” does not mean “no third-party processing”.
- The local prototype has no production authentication or tenant isolation; it should not be exposed as a public lending service without additional controls.

Recommended `.gitignore` entries:

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
.pytest_cache/
*.pyc
```

If a key has been committed or shared, revoke it, create a replacement and clean the tracked template. Deleting a file or adding `.gitignore` does not remove secrets from previous commits.

## Limitations

- Extraction can misread digits or handwriting. Users must confirm fields.
- Reader confidence is uncalibrated model self-report.
- Explanation safeguards constrain numbers and references, but do not guarantee complete semantic faithfulness.
- The payslip divisor and applicable allowances require confirmation; the configured rule is not a legal verdict.
- Bill uses a February 2024 historical tariff, not verified current tariff compliance.
- Loan calculations assume equal end-of-month payments and the specified upfront fee; undisclosed charges change the result.
- The tamper classifier was developed using synthetic images. Real-world accuracy is unknown, and genuine photos can trigger warnings.
- All Verify outcomes support human review; none proves authenticity or fraud.
- Live reading, explanation and cloud speech depend on provider availability, supported models, internet and quota.

## Next steps

Potential next steps include current rule-pack verification, representative consented evaluation where permitted, confidence calibration, stronger name matching, reviewer workflow integration and production access controls. These are proposed improvements, not existing partnerships or deployed integrations.

## Demo

[▶ Watch the Kagoj Bondhu demo]([assets/demo.mp4](https://drive.google.com/file/d/1lUDwsQslYKHLC5hfXMZ9Sr6t2DKzrsKz/view?usp=sharing)
