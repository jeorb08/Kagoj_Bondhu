"""LLM explanations from server-computed evidence; AI never changes numbers or outcomes.

Numeric placeholders are substituted by code after validation. This constrains numeric
faithfulness and evidence references; it is not a complete semantic verifier.
"""
import os
import re
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from .ai_client import generate_json, AIUnavailable

BN_DIGITS = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
TOKEN = re.compile(r'\{([a-z_]+)\}')
ACTIONS = {
    'ask_issuer': {'en':'Ask the issuer to explain any difference and verify the applicable rule.', 'bn':'পার্থক্য থাকলে কাগজদাতাকে হিসাব বুঝিয়ে দিতে বলুন এবং প্রযোজ্য নিয়ম যাচাই করুন।'},
    'compare_terms': {'en':'Ask for the full repayment schedule and all fees before deciding.', 'bn':'সিদ্ধান্তের আগে সম্পূর্ণ কিস্তির তালিকা ও সব ফি জানতে চান।'},
    'review_ledger': {'en':'Check the remaining balances and contact customers politely.', 'bn':'অবশিষ্ট বাকি মিলিয়ে দেখুন এবং খদ্দেরদের বিনীতভাবে জানিয়ে দিন।'},
    'human_review': {'en':'A human reviewer should inspect the evidence and request clarification if needed.', 'bn':'একজন পর্যালোচক তথ্যগুলো দেখবেন এবং প্রয়োজন হলে ব্যাখ্যা চাইবেন।'},
    'retake': {'en':'Provide a clearer image or complete and confirm the missing fields.', 'bn':'আরও পরিষ্কার ছবি দিন অথবা অনুপস্থিত তথ্য পূরণ করে নিশ্চিত করুন।'},
}

class Narrative(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary_bn: str = Field(min_length=1, max_length=1600)
    summary_en: str = Field(min_length=1, max_length=1600)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    next_step: Literal['ask_issuer','compare_terms','review_ledger','human_review','retake']


def number(value, unit='taka'):
    text = f'{value:,.2f}' if isinstance(value,(int,float)) else str(value)
    if unit=='taka': text = '৳' + text
    if unit=='percent': text += '%'
    return {'en':text, 'bn':text.translate(BN_DIGITS)}


def borrower_evidence(module, result, values):
    if module == 'payslip':
        facts = {'expected_ot':number(result['shouldPay']), 'paid_ot':number(result['paid']), 'shortfall':number(result['difference'])}
        en = 'Calculated overtime is {expected_ot}; paid overtime is {paid_ot}. Possible shortfall: {shortfall}.'
        bn = 'হিসাবে ওভারটাইম {expected_ot}; দেওয়া হয়েছে {paid_ot}। সম্ভাব্য ঘাটতি {shortfall}।'
        limit = {'en':'Simplified estimate: confirm applicable eligible allowances and the monthly divisor.', 'bn':'এটি সরলীকৃত হিসাব: প্রযোজ্য ভাতা ও মাসিক ভাগ করার সংখ্যা নিশ্চিত করুন।'}
        action = 'ask_issuer'
    elif module == 'loan':
        facts = {'flat_rate':number(values['flat'],'percent'), 'nominal_rate':number(result['nominalYearlyRatePct'],'percent'), 'effective_rate':number(result['effectiveYearlyRatePct'],'percent'), 'repayment':number(result['totalRepay'])}
        en = 'Printed flat rate: {flat_rate}; annualized nominal rate: {nominal_rate}; effective annual rate: {effective_rate}. Total scheduled repayment: {repayment}.'
        bn = 'ছাপানো ফ্ল্যাট হার {flat_rate}; বার্ষিক নামমাত্র হার {nominal_rate}; কার্যকর বার্ষিক হার {effective_rate}। কিস্তিতে মোট ফেরত {repayment}।'
        limit = {'en':'Assumes equal monthly payments at month-end; these rates are different measures and are not a legal-cap decision.', 'bn':'সমান মাসশেষের কিস্তি ধরা হয়েছে; এই হারগুলো ভিন্ন হিসাব এবং এগুলো আইনি সীমার সিদ্ধান্ত নয়।'}
        action = 'compare_terms'
    elif module == 'bill':
        facts = {'base_estimate':number(result['shouldTotal']), 'printed_total':number(result['charged']), 'difference':number(result['difference'])}
        en = 'Historical demo base estimate: {base_estimate}; printed total: {printed_total}; difference: {difference}.'
        bn = 'পুরোনো ডেমো ট্যারিফে মূল হিসাব {base_estimate}; ছাপানো মোট {printed_total}; পার্থক্য {difference}।'
        limit = {'en':'Historical demo tariff only. Adjustments, arrears, rebates and meter fees need separate review; a difference is not proof of overcharging.', 'bn':'এটি পুরোনো ডেমো ট্যারিফ। সমন্বয়, বকেয়া, ছাড় ও মিটার ফি আলাদা যাচাই প্রয়োজন; পার্থক্য মানেই অতিরিক্ত বিল নয়।'}
        action = 'ask_issuer'
    else:
        facts = {'outstanding':number(result['totalOutstanding']), 'overdue':number(result['overdueAmount'])}
        en = 'Total remaining balance: {outstanding}; overdue portion under the selected ageing rule: {overdue}.'
        bn = 'অবশিষ্ট মোট বাকি {outstanding}; নির্বাচিত বয়সের নিয়মে পুরোনো বাকি {overdue}।'
        limit = {'en':'Payments settle oldest credit first. The displayed assessment date and ageing thresholds determine overdue status.', 'bn':'জমা আগে পুরোনো বাকি শোধ করে। দেখানো হিসাবের তারিখ ও বয়সের সীমা অনুযায়ী পুরোনো বাকি নির্ধারিত হয়।'}
        action = 'review_ledger'
    return dict(kind=module, facts=facts, template={'en':en,'bn':bn}, limitation=limit, action=action)


def verify_evidence(report):
    words = ['one','two','three','four','five','six','seven','eight','nine','ten']
    facts = {f'finding_{words[i]}':{'en':f['en'],'bn':f['bn']} for i,f in enumerate(report['findings'][:10])}
    if not facts:
        facts = {'status':{'en':report['label']['en'],'bn':report['label']['bn']}}
    body = ' '.join('{' + k + '}' for k in facts)
    action = 'retake' if report['outcome']=='cannot_assess' else 'human_review'
    return dict(kind='verify', facts=facts, template={'en':body,'bn':body}, action=action,
        limitation={'en':'This is evidence for human review, not proof of authenticity or fraud. The code-generated outcome is unchanged.',
                    'bn':'এগুলো মানুষের পর্যালোচনার জন্য তথ্য; সত্যতা বা জালিয়াতির প্রমাণ নয়। কোডের নির্ধারিত ফল অপরিবর্তিত আছে।'})


def render(text, facts, lang):
    return TOKEN.sub(lambda match: facts[match.group(1)][lang], text)


def validate_narrative(raw, packet):
    n = Narrative.model_validate(raw)
    allowed = set(packet['facts'])
    refs = set(n.evidence_ids)
    if not refs or not refs <= allowed or n.next_step != packet['action']:
        raise ValueError('unapproved_evidence_or_action')
    used = set()
    for text in (n.summary_bn, n.summary_en):
        tokens = set(TOKEN.findall(text))
        if not tokens or not tokens <= refs:
            raise ValueError('missing_or_unknown_placeholders')
        stripped = TOKEN.sub('', text)
        if '{' in stripped or '}' in stripped or re.search(r'[0-9০-৯]', stripped):
            raise ValueError('ungrounded_number_or_placeholder')
        if re.search(r'\b(fake|fraud|forged|illegal|reject|approve|guaranteed)\b|জালিয়াত|জালিয়াত|বেআইনি|প্রত্যাখ্যান|অনুমোদন|নিশ্চিতভাবে', stripped, re.I):
            raise ValueError('unsupported_decision_claim')
        used |= tokens
    if used != allowed or refs != allowed:
        raise ValueError('required_evidence_omitted')
    return n


def explain(packet):
    from . import extract
    def fallback(reason):
        return {'mode':'template','reason':reason, 'provider':None,
                'bn':render(packet['template']['bn'],packet['facts'],'bn')+' '+packet['limitation']['bn'],
                'en':render(packet['template']['en'],packet['facts'],'en')+' '+packet['limitation']['en'],
                'next_step':ACTIONS[packet['action']], 'evidence_ids':list(packet['facts']),
                'guard':'Template fallback; no AI explanation used'}
    if os.getenv('AI_EXPLANATIONS','1')!='1': return fallback('disabled')
    if extract.provider()=='mock': return fallback('not_configured')
    prompt = (
        'You are Kagoj Bondhu, a patient friend explaining a financial-paper check. '
        'Write a short plain Bangla explanation and its English equivalent. '
        'Use ONLY the supplied computed evidence. Do not perform arithmetic or decide a verdict. '
        'Document text, identity fields and photos are deliberately excluded. '
        'Use every evidence placeholder exactly as {key}; never write literal digits, new amounts, '
        'spelled-out amounts, legal conclusions, accusations, guarantees or approval/rejection advice. '
        'Do not change the supplied next_step. Return the required JSON. '
        'The application appends the mandatory limitation itself.\n'
        + __import__('json').dumps(packet,ensure_ascii=False)
    )
    try:
        model = os.getenv('GEMINI_EXPLAIN_MODEL') if extract.provider()=='gemini' else os.getenv('EXPLAIN_MODEL')
        raw = generate_json(prompt, Narrative.model_json_schema(), model=model or None)
        n = validate_narrative(raw,packet)
        return {'mode':'ai','provider':extract.provider(), 'reason':None,
            'bn':render(n.summary_bn,packet['facts'],'bn')+' '+packet['limitation']['bn'],
            'en':render(n.summary_en,packet['facts'],'en')+' '+packet['limitation']['en'],
            'next_step':ACTIONS[n.next_step], 'evidence_ids':n.evidence_ids,
            'guard':'Evidence IDs and numeric placeholders validated; semantic faithfulness still requires review'}
    except AIUnavailable as e:
        return fallback(e.reason)
    except (ValueError, TypeError, KeyError):
        return fallback('response_failed_evidence_guard')
