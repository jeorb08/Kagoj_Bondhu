"""Comparison of human-confirmed fields; no authenticity or lending decision."""
import math
import re
import unicodedata
from datetime import date

def name_key(value):
    return ''.join(c for c in unicodedata.normalize('NFKC',value).casefold() if c.isalnum())

def clean(kind, values):
    if kind not in ('payslip','application'): raise ValueError('Unsupported comparison document')
    out={}
    for key in ('name','emp_id','period'):
        value=values.get(key)
        if value is not None and str(value).strip():
            value=str(value).strip()
            if len(value)>160: raise ValueError('Text field too long')
            out[key]=value
    if out.get('period'):
        if not re.fullmatch(r'\d{4}-\d{2}',out['period']): raise ValueError('Period must be YYYY-MM')
        date.fromisoformat(out['period']+'-01')
    key='net' if kind=='payslip' else 'declared_income'
    raw=values.get(key)
    if raw is not None and raw!='':
        n=float(raw)
        if not math.isfinite(n) or n<0 or n>1e12: raise ValueError('Income must be finite and nonnegative')
        out['income']=n
    return out

def compare(left, right):
    if not left['confirmed'] or not right['confirmed']: raise ValueError('Confirm both documents before comparing')
    a=clean(left['kind'],left['values']); b=clean(right['kind'],right['values']); rows=[]
    def row(field, status, reason): rows.append({'field':field,'left':a.get(field),'right':b.get(field),'status':status,'reason':reason})
    for key in ('name','emp_id'):
        if key not in a or key not in b: row(key,'missing','Cannot compare: field missing in one or both documents.'); continue
        match=name_key(a[key])==name_key(b[key]) if key=='name' else a[key].casefold()==b[key].casefold()
        row(key,'match' if match else 'review','Normalized values agree.' if match else 'Values differ. Spelling, transliteration or a different person may explain this; ask a reviewer.')
    same=a.get('period') and a.get('period')==b.get('period')
    row('period','missing' if not a.get('period') or not b.get('period') else 'match' if same else 'context','Month missing; income comparison lacks time context.' if not a.get('period') or not b.get('period') else 'Same month.' if same else 'Different months: income can legitimately change.')
    compatible=left['kind']==right['kind'] or right['values'].get('income_basis')=='net' and left['kind']=='payslip' or left['values'].get('income_basis')=='net' and right['kind']=='payslip'
    if 'income' not in a or 'income' not in b: row('income','missing','Income missing; cannot compare.')
    elif not compatible: row('income','context','Declared income basis is unspecified or gross; it is not directly comparable with net pay.')
    elif not same: row('income','context','Income shown for context only: months differ or are missing. No income mismatch flag.')
    else:
        delta=round(b['income']-a['income'],2)
        row('income','match' if abs(delta)<=1 else 'review',f'Right minus left = {delta:.2f} taka. Same month and net basis; a difference needs explanation, not a fraud conclusion.')
    review=any(x['status']=='review' for x in rows)
    complete=all(x['status']=='match' for x in rows)
    return {'outcome':'needs_review' if review else 'looks_consistent' if complete else 'cannot_assess','rows':rows,'limitations':'Confirmed field comparison only. No document authenticity certification, automatic rejection, name transliteration matching, or real-world accuracy claim.'}
