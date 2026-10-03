"""Provider adapters. Secrets remain on the server; no document text is logged."""
import json
import os
import re
import time
import urllib.error
import urllib.request

class AIUnavailable(RuntimeError):
    def __init__(self, reason, status=None):
        self.reason = reason
        self.status = status
        super().__init__(reason)


def timeout():
    return max(5, min(60, int(os.getenv('AI_TIMEOUT_SECONDS', '40'))))


def gemini_request(body, model=None, deadline=None):
    key = os.getenv('GEMINI_API_KEY', '').strip()
    model = (model or os.getenv('GEMINI_MODEL', '')).strip().removeprefix('models/')
    if not key or not model:
        raise AIUnavailable('not_configured')
    if not re.fullmatch(r'[A-Za-z0-9._-]+', model):
        raise AIUnavailable('invalid_model_name')
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(), method='POST',
        headers={'Content-Type':'application/json', 'x-goog-api-key':key})
    deadline = deadline if deadline is not None else time.monotonic() + timeout()
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AIUnavailable('request_timeout')
        try:
            with urllib.request.urlopen(req, timeout=remaining) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            # Never return raw provider bodies: they can echo document text or credentials.
            reason = {400:'invalid_request_or_model',401:'invalid_api_key',403:'access_denied',
                      404:'model_not_available',408:'request_timeout',413:'image_too_large',
                      429:'quota_busy',500:'provider_internal_error',502:'provider_gateway_error',
                      503:'provider_overloaded',504:'provider_timeout'}.get(e.code,'provider_http_error')
            delay = 0.5 * 2**attempt
            if e.code in (500,502,503,504) and attempt < 2 and deadline-time.monotonic()>delay+1:
                time.sleep(delay)
                continue
            raise AIUnavailable(reason, e.code) from None
        except TimeoutError:
            raise AIUnavailable('request_timeout') from None
        except (OSError, ValueError):
            raise AIUnavailable('connection_or_response_error') from None


def public_error(error):
    reason = getattr(error, 'reason', str(error))
    messages = {
        'not_configured':'Set the API key and reading model in .env, then restart.',
        'invalid_api_key':'The reading service rejected the API key.',
        'access_denied':'The reading service denied access. Check the key permissions and API availability.',
        'model_not_available':'The configured model is unavailable. Run configure_ai.py to select an available model.',
        'quota_busy':'The reading quota is exhausted or busy. Wait and retry.',
        'provider_overloaded':'The reading service is overloaded. Automatic retries failed; retry shortly.',
        'provider_internal_error':'The reading service returned an internal error after retries.',
        'provider_gateway_error':'The reading service gateway failed after retries.',
        'provider_timeout':'The reading service timed out after retries.',
        'request_timeout':'The reading request timed out. Retry or use a smaller photo.',
        'invalid_request_or_model':'The reading service rejected the image or request format.',
        'connection_or_response_error':'Could not connect to the reading service or decode its response.',
        'invalid_json_response':'The reader returned invalid data. Retry; no numbers were guessed.',
        'no_response':'The reader returned no usable content. Retry or enter fields manually.',
        'image_too_large':'The reading service rejected the image size. Upload a smaller photo.',
    }
    status = getattr(error, 'status', None)
    suffix = f' (provider HTTP {status})' if status else ''
    return messages.get(reason, 'The reading service failed.') + suffix + f' [{reason}]'


def generate_json(prompt, schema, image=None, model=None, provider=None):
    from . import extract
    provider = provider or extract.provider()
    if provider == 'gemini':
        parts = []
        if image:
            media, data = image
            parts.append({'inlineData':{'mimeType':media,'data':data}})
        parts.append({'text':prompt})
        deadline = time.monotonic() + timeout()
        body = {'contents':[{'role':'user','parts':parts}],
                'generationConfig':{'responseMimeType':'application/json','responseJsonSchema':schema,'temperature':0}}
        try:
            payload = gemini_request(body, model=model, deadline=deadline)
        except AIUnavailable as e:
            # Some model revisions fail on a structured schema even when ordinary requests work.
            # One JSON-mode fallback retains the schema in the prompt; local validation still applies.
            if e.reason not in ('invalid_request_or_model','provider_internal_error') or deadline-time.monotonic()<2:
                raise
            fallback_parts = [dict(p) for p in parts]
            fallback_parts[-1] = {'text':prompt + '\nReturn only JSON matching this schema: ' + json.dumps(schema,ensure_ascii=False)}
            payload = gemini_request({'contents':[{'role':'user','parts':fallback_parts}],
                'generationConfig':{'responseMimeType':'application/json','temperature':0}},
                model=model, deadline=deadline)
        candidates = payload.get('candidates') or []
        if not candidates:
            raise AIUnavailable('no_response')
        text = ''.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if not p.get('thought'))
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
        try:
            result = json.loads(text)
        except (ValueError, TypeError):
            raise AIUnavailable('invalid_json_response') from None
    elif provider == 'anthropic':
        try:
            import anthropic
            client = anthropic.Anthropic(timeout=timeout(), max_retries=0)
            content = []
            if image:
                media, data = image
                content.append({'type':'image','source':{'type':'base64','media_type':media,'data':data}})
            content.append({'type':'text','text':prompt})
            response = client.messages.create(
                model=model or os.environ['MODEL'], max_tokens=5000,
                tools=[{'name':'record_result','description':'Record the structured result.','input_schema':schema}],
                tool_choice={'type':'tool','name':'record_result'},
                messages=[{'role':'user','content':content}])
            block = next((b for b in response.content if b.type=='tool_use'),None)
            if block is None: raise AIUnavailable('no_response')
            result = block.input
        except AIUnavailable:
            raise
        except Exception:
            raise AIUnavailable('anthropic_unavailable') from None
    else:
        raise AIUnavailable('not_configured')
    if not isinstance(result,dict):
        raise AIUnavailable('invalid_json_response')
    return result
