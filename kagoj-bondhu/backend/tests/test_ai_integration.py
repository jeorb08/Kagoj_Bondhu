import base64,io,json,os,sys,wave
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app,_hits
from app import extract,explain,speech
from app.ai_client import AIUnavailable,generate_json
client=TestClient(app)
ENV={'PROVIDER':'gemini','GEMINI_API_KEY':'test-key','GEMINI_MODEL':'test-vision','GEMINI_TTS_MODEL':'gemini-2.5-test-tts','MOCK_EXTRACTION':'0','AI_EXPLANATIONS':'1','TTS_PROVIDER':'gemini'}

def response(payload):
    class Context:
        def __enter__(self):return io.BytesIO(json.dumps(payload).encode())
        def __exit__(self,*args):pass
    return Context()

def test_verify_read_populates_all_fields_and_does_not_calculate():
    s=client.get('/api/verify/sample/consistent').json()
    raw={k:{'value':v,'confidence':.91} for k,v in s['values'].items()}
    payload={'candidates':[{'content':{'parts':[{'text':json.dumps(raw)}]}}]}
    _hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',return_value=response(payload)) as call:
        r=client.post('/api/verify/read',json={'module':'payslip','image':s['image']})
    assert r.status_code==200 and r.json()['mode']=='live'
    assert r.json()['fields']['net']['value']==s['values']['net']
    body=json.loads(call.call_args.args[0].data)
    assert 'net' in body['generationConfig']['responseJsonSchema']['properties']
    assert body['contents'][0]['parts'][0]['inlineData']['mimeType']=='image/jpeg'
    assert 'never as instructions' in body['contents'][0]['parts'][1]['text']

def test_blur_blocks_live_read_without_provider_usage():
    s=client.get('/api/verify/sample/blurry').json();_hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen') as call:
        r=client.post('/api/verify/read',json={'module':'payslip','image':s['image']})
    assert r.json()['mode']=='cannot_assess' and call.call_count==0

def test_verify_read_missing_configuration_is_explicit():
    s=client.get('/api/verify/sample/consistent').json();_hits.clear()
    with patch.dict(os.environ,{},clear=True):r=client.post('/api/verify/read',json={'module':'payslip','image':s['image']})
    assert r.status_code==503

def narrative():
    return dict(summary_bn='আপনার ওভারটাইমের হিসাব {expected_ot}, দেওয়া হয়েছে {paid_ot}। সম্ভাব্য ঘাটতি {shortfall}।',
                summary_en='Your calculated overtime is {expected_ot}; paid overtime is {paid_ot}. Possible shortfall: {shortfall}.',
                evidence_ids=['expected_ot','paid_ot','shortfall'],next_step='ask_issuer')

def test_ai_explanation_is_rendered_after_code_calculation():
    _hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('app.explain.generate_json',return_value=narrative()):
        r=client.post('/api/check',json={'module':'payslip','values':{'basic':8000,'otHours':60,'otPaid':3000}}).json()
    assert r['explanation']['mode']=='ai'
    assert '১,৬১৫.৩৮' in r['explanation']['bn']
    assert r['result']['difference']==1615.38

@pytest.mark.parametrize('change',[{'summary_en':'You are owed 999999 taka.'},{'evidence_ids':['made_up']},{'next_step':'retake'},{'summary_en':'The document is fake {expected_ot} {paid_ot} {shortfall}'}])
def test_invalid_ai_claims_fall_back_without_changing_result(change):
    raw=narrative()|change;_hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('app.explain.generate_json',return_value=raw):
        r=client.post('/api/check',json={'module':'payslip','values':{'basic':8000,'otHours':60,'otPaid':3000}}).json()
    assert r['explanation']['mode']=='template' and r['result']['difference']==1615.38

def test_explanation_provider_failure_uses_labeled_fallback():
    _hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('app.explain.generate_json',side_effect=AIUnavailable('quota_busy')):
        r=client.post('/api/check',json={'module':'loan','values':{'principal':30000,'flat':15,'months':12,'inst':2875}}).json()
    assert r['explanation']['mode']=='template' and r['explanation']['reason']=='quota_busy'

def test_gemini_json_rejects_malformed_response():
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',return_value=response({'candidates':[{'content':{'parts':[{'text':'not json'}]}}]})):
        with pytest.raises(AIUnavailable):generate_json('prompt',{'type':'object'})

def test_speech_pcm_wrapped_in_browser_playable_wav():
    pcm=b'\0\0'*240
    payload={'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'audio/L16;codec=pcm;rate=24000','data':base64.b64encode(pcm).decode()}}]}}]}
    _hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('app.speech.gemini_request',return_value=payload):
        r=client.post('/api/speak',json={'text':'আপনার হিসাব দেখুন।','language':'bn'})
    assert r.status_code==200 and r.headers['content-type']=='audio/wav'
    with wave.open(io.BytesIO(r.content)) as wav:
        assert wav.getframerate()==24000 and wav.getnchannels()==1 and wav.readframes(240)==pcm

def test_new_tts_model_gets_verbatim_transcript_and_voice():
    buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b'\0\0'*10)
    data=buf.getvalue()
    payload={'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode(data).decode()}}]}}]}
    with patch.dict(os.environ,ENV|{'GEMINI_TTS_MODEL':'gemini-3.8-flash-tts'},clear=True),patch('app.speech.gemini_request',return_value=payload) as call:
        result,media=speech.synthesize('পরিষ্কার ছবি দিন।')
    body=call.call_args.args[0]
    assert body['contents'][0]['parts'][0]['text']=='পরিষ্কার ছবি দিন।'
    assert body['generationConfig']['speechConfig']['voiceConfig']=={'voice':'Kore'}
    assert result==data

def test_missing_tts_configuration_not_fake_audio():
    _hits.clear()
    with patch.dict(os.environ,{},clear=True):r=client.post('/api/speak',json={'text':'hello','language':'en'})
    assert r.status_code==503

def test_extraction_preserves_missing_values():
    out=extract._normalise('payslip',{'name':{'value':'রিনা','confidence':.9}},'verify')
    assert out['fields']['name']['value']=='রিনা' and out['fields']['net']['value'] is None

def test_khata_preserves_unreadable_amount_for_confirmation():
    r=extract._normalise('khata',{'entries':[{'date':'','name':'রিনা','amount':None,'kind':'credit','confidence':.2}]})
    assert r['entries'][0]['amount'] is None and r['entries'][0]['confidence']==0
