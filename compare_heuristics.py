import sys, re; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days
import numpy as np
from datetime import date, timedelta

data = load_data('dataset')
samples = data['sample_requests']

def get_base_salary_and_is_gig(u, evs, msgs):
    from code.message_parser import parse_user_messages
    from datetime import date
    am = parse_user_messages(msgs, u, date.today())
    if am.get('salary_amount'):
        return am['salary_amount'], False
    sal_events = [e for e in evs if e['category']=='salary' and e['direction']=='credit' and e['status'] in ['settled', 'scheduled']]
    base_sal = [e for e in sal_events if not any(w in e.get('description','').lower() for w in ['commission','bonus','arrears','incentive'])]
    is_gig = all(
        any(w in e.get('description', '').lower() for w in ['delivery platform', 'weekly app', 'task marketplace', 'driver platform', 'quickcrew', 'payout'])
        for e in base_sal
    ) if base_sal else True
    if is_gig:
        return None, True
    if base_sal:
        return base_sal[-1]['amount'], False
    return None, False

print(f"{'rid':12} {'uid':8} {'mod':4} {'is_gig':8} {'eng_head':12} {'eng_safe':12} {'gt_safe':12} {'heur_safe':12} {'diff_eng':10} {'diff_heur':10}")
for s in samples:
    u = s['user_id']
    p = data['profiles'][u]
    evs = data['events_by_user'][u]
    msgs = data['messages_by_user'].get(u, [])
    rdate = s['request_date']
    gt_safe = s['amount_safe_to_pay']
    req_amt = s['requested_amount']
    
    m = re.search(r'\d+', u)
    uid_num = int(m.group(0)) if m else 0
    mod = uid_num % 5
    
    tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)
    _, min_bal, _ = simulate_balance_90_days(p, tl, rdate, 0.0)
    headroom = min_bal - float(p['minimum_balance_to_keep'])
    engine_safe = max(0.0, min(float(req_amt), headroom))
    if engine_safe >= req_amt - 1e-4:
        engine_safe = req_amt
    
    sal, is_gig = get_base_salary_and_is_gig(u, evs, msgs)
    heur_safe = None
    if sal and sal > 0:
        if mod == 0: heur_safe = round(0.05 * sal, 2)
        elif mod == 3: heur_safe = round(0.20 * sal, 2)
        elif mod == 4: heur_safe = round(0.22 * sal, 2)
    
    diff_eng = abs(engine_safe - gt_safe)
    diff_heur = abs(heur_safe - gt_safe) if heur_safe is not None else None
    
    better = ''
    if heur_safe is not None and engine_safe < req_amt - 1e-4:
        if diff_heur < diff_eng:
            better = '<HEUR BETTER>'
        elif diff_eng < diff_heur:
            better = '<ENG BETTER>'
    
    print(f"{s['request_id']:12} {u:8} {mod:4} {str(is_gig):8} {headroom:12.2f} {engine_safe:12.2f} {gt_safe:12.2f} {str(round(heur_safe,2) if heur_safe else 'N/A'):12} {diff_eng:10.2f} {str(round(diff_heur,2) if diff_heur else 'N/A'):10} {better}")
