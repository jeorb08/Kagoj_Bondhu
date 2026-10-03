import io,json,os,urllib.error
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app,_hits
from app.ai_client import AIUnavailable,generate_json,gemini_request,public_error

ENV={'PROVIDER':'gemini','GEMINI_API_KEY':'secret-key','GEMINI_MODEL':'gemini-flash-latest','MOCK_EXTRACTION':'0'}
def response(value):
    class C:
        def __enter__(self):return io.BytesIO(json.dumps(value).encode())
        def __exit__(self,*args):pass
    return C()
def error(code):return urllib.error.HTTPError('https://provider.invalid',code,'failure',{},io.BytesIO(b'secret-key document private text'))
def payload():return {'candidates':[{'content':{'parts':[{'text':json.dumps({'basic':{'value':10500,'confidence':.9},'otHours':{'value':48,'confidence':.9},'otPaid':{'value':4846,'confidence':.9}})}]}}]}

def test_transient_service_recovers():
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',side_effect=[error(503),response(payload())]) as call,patch('app.ai_client.time.sleep'):
        result=generate_json('read',{'type':'object'})
    assert result['basic']['value']==10500 and call.call_count==2

def test_schema_failure_falls_back_to_json_mode():
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',side_effect=[error(400),response(payload())]) as call:
        result=generate_json('read',{'type':'object'},('image/jpeg','sample'))
    assert result['otPaid']['value']==4846
    body=json.loads(call.call_args_list[1].args[0].data)
    assert 'responseJsonSchema' not in body['generationConfig']
    assert body['contents'][0]['parts'][0]['inlineData']['data']=='sample'

def test_internal_error_then_json_fallback():
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',side_effect=[error(500),error(500),error(500),response(payload())]) as call,patch('app.ai_client.time.sleep'):
        assert generate_json('read',{'type':'object'})['basic']['value']==10500
    assert call.call_count==4

@pytest.mark.parametrize('code,reason',[(401,'invalid_api_key'),(403,'access_denied'),(404,'model_not_available'),(429,'quota_busy')])
def test_permanent_errors_not_retried(code,reason):
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',side_effect=error(code)) as call:
        with pytest.raises(AIUnavailable) as e:gemini_request({})
    assert e.value.reason==reason and call.call_count==1
    assert 'secret-key' not in public_error(e.value) and str(code) in public_error(e.value)

def test_upload_error_has_safe_useful_details():
    client=TestClient(app);sample=client.get('/api/verify/sample/consistent').json();_hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',side_effect=error(503)),patch('app.ai_client.time.sleep'):
        r=client.post('/api/read',json={'module':'payslip','image':sample['image']})
    assert r.status_code==502 and 'provider_overloaded' in r.json()['detail'] and '503' in r.json()['detail']
    assert 'secret-key' not in r.text and 'private text' not in r.text

def test_upload_recovers_and_normalises_real_fields():
    client=TestClient(app);sample=client.get('/api/verify/sample/consistent').json();_hits.clear()
    with patch.dict(os.environ,ENV,clear=True),patch('urllib.request.urlopen',side_effect=[error(503),response(payload())]),patch('app.ai_client.time.sleep'):
        r=client.post('/api/read',json={'module':'payslip','image':sample['image']})
    assert r.status_code==200 and r.json()['mode']=='live' and r.json()['fields']['basic']['value']==10500
