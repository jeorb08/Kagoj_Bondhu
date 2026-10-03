import pytest
from app.comparison import compare
from app.rules import check
from app.proof import build

def pair(period='2026-05',basis='net'):
    return {'kind':'payslip','confirmed':True,'values':{'name':'Rina Islam','emp_id':'X1','period':'2026-05','net':24000}}, {'kind':'application','confirmed':True,'values':{'name':'rina  islam','emp_id':'X1','period':period,'declared_income':28000,'income_basis':basis}}

def test_difference():
    a,b=pair();assert compare(a,b)['outcome']=='needs_review'

@pytest.mark.parametrize('period,basis',[('2026-06','net'),('2026-05','gross'),('', 'net')])
def test_context(period,basis):
    a,b=pair(period,basis);r=compare(a,b);assert r['outcome']=='cannot_assess';assert r['rows'][-1]['status']=='context'

def test_confirmation():
    a,b=pair();b['confirmed']=False
    with pytest.raises(ValueError):compare(a,b)

@pytest.mark.parametrize('value',[float('nan'),-1,float('inf')])
def test_invalid(value):
    a,b=pair();b['values']['declared_income']=value
    with pytest.raises(ValueError):compare(a,b)

def test_match():
    a,b=pair();b['values']['declared_income']=24000;assert compare(a,b)['outcome']=='looks_consistent'

def test_proof():
    v={'basic':11500,'otHours':47,'otPaid':5197};r=check('payslip',v);p=build('payslip',v,r)
    assert p['inputs']==v;assert str(r['difference']) in p['steps'][-1]

def test_api():
    from fastapi.testclient import TestClient
    from app.main import app
    a,b=pair();r=TestClient(app).post('/api/verify/compare',json={'left':a,'right':b});assert r.status_code==200

def test_application_schema():
    from app.extract import _tool_for, _normalise
    schema=_tool_for('application','verify')['input_schema']
    assert schema['properties']['period']['properties']['value']['type']==['string','null']
    fields=_normalise('application',{'declared_income':{'value':28000,'confidence':.9}},'verify')['fields']
    assert fields['declared_income']['value']==28000 and fields['period']['value'] is None

@pytest.mark.parametrize('module,v',[('loan',{'principal':10000,'flat':10,'months':12,'inst':920}),('bill',{'units':100,'demand':42,'total':600}),('khata',{'entries':[{'name':'Rina','date':'2026-01-01','amount':100,'kind':'credit'}]})])
def test_other_proofs(module,v):
    assert build(module,v,check(module,v))['steps']
