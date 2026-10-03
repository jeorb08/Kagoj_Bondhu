"""Reviewable evidence assembled from confirmed inputs and server results."""
from .rules import load_pack

def build(module, values, result):
    pack=load_pack(module); p=pack['params']; v=values; x=result
    if module=='payslip':
        steps=[f"Hourly wage = ({v['basic']} + {v.get('eligibleAllowance',0)}) / {p['monthly_divisor']} = {x['hourlyWage']}",f"Overtime rate = hourly wage × {p['overtime_multiplier']} = {x['overtimeRate']}",f"Expected overtime = unrounded overtime rate × {v['otHours']} hours = {x['shouldPay']}",f"Possible shortfall = max(expected − {x['paid']}, 0) = {x['difference']}"]
        limits='208 is a demo divisor pending applicable-rule confirmation. Eligible allowances must be confirmed. Intermediate values are displayed rounded; calculations use full precision.'
    elif module=='loan':
        steps=[f"Net received = principal − upfront fee = {x['netDisbursed']}",f"Total repayment = {v['inst']} × {v['months']} = {x['totalRepay']}",f"Solve net received = sum(payment / (1 + r)^month); monthly r = {x['monthlyRatePct']}%",f"Effective annual rate = ((1 + unrounded r)^12 − 1) × 100 = {x['effectiveYearlyRatePct']}%",f"Flat-rate installment estimate = principal × (1 + flat/100 × months/12) / months = {x['expectedInstallment']}"]
        limits=x['assumptions']
    elif module=='bill':
        steps=[f"{s['units']} kWh × {s['rate']} = {s['amount']}" for s in x['slabs']]+[f"Energy = {x['energy']}; demand = {x['demand']}",f"VAT = (energy + demand) × {p['vat_percent']}% = {x['vat']}",f"Base estimate = energy + demand + VAT = {x['shouldTotal']}",f"Printed total − base estimate = {x['difference']}"]
        limits=x['assumptions']
    else:
        steps=[f"Assessment date: {x['asOf']}; payments settle oldest credit first",f"Overdue threshold: older than {p['overdue_days']} days"]+[f"{c['name']}: remaining balance {c['balance']}; oldest unpaid {c['oldest']}; overdue balance {c['overdueBalance']}" for c in x['customers']]+[f"Total remaining balance = {x['totalOutstanding']}; overdue portion = {x['overdueAmount']}"]
        limits='Ledger age is a bookkeeping indicator, not a prediction of whether someone will repay.'
    return {'inputs':v,'steps':steps,'rule_name':pack['id'],'rule_version':pack['version'],'source':pack['source'],'rule_date':'February 2024 historical snapshot' if module=='bill' else 'No effective date verified in this demo pack','limitations':limits}
