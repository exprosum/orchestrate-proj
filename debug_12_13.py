import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days, calc_amount_safe_to_pay
from datetime import date, timedelta
from collections import defaultdict

data = load_data('dataset')

for rid in ['request_13', 'request_12']:
    s = [x for x in data['sample_requests'] if x['request_id']==rid][0]
    u = s['user_id']
    p = data['profiles'][u]
    evs = data['events_by_user'][u]
    msgs = data['messages_by_user'].get(u, [])
    rdate = s['request_date']
    
    print(f"=== {rid} (user={u}) ===")
    print(f"  GT safe:    {s['amount_safe_to_pay']}")
    print(f"  Req amount: {s['requested_amount']}")
    print(f"  Curr bal:   {p['current_available_balance']}")
    print(f"  Min keep:   {p['minimum_balance_to_keep']}")
    print(f"  GT date:    {s['earliest_date_for_full_payment']}")
    print(f"  GT status:  {s['affordability_status']}")
    print(f"  Explanation: {s['decision_explanation'][:300]}")
    
    tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)
    _, min_bal, _ = simulate_balance_90_days(p, tl, rdate, 0.0)
    engine_safe = calc_amount_safe_to_pay(p, evs, msgs, rdate, s['requested_amount'])
    print(f"  Engine headroom: {min_bal - float(p['minimum_balance_to_keep']):.4f}")
    print(f"  Engine safe: {engine_safe:.4f}")
    print(f"  Diff: {abs(engine_safe - s['amount_safe_to_pay']):.4f}")
    
    print("  Debits by category:")
    cat_debits = defaultdict(float)
    for d in tl:
        for it in tl[d]:
            if it['type'] == 'debit': cat_debits[it.get('category','?')] += it['amount']
    for cat, amt in sorted(cat_debits.items(), key=lambda x: -x[1]):
        print(f'    {cat:30} {amt:12.4f}')
    print(f'    TOTAL: {sum(cat_debits.values()):17.4f}')
    
    # Show where min balance happens
    balance = float(p['current_available_balance'])
    min_b = balance
    min_d = rdate
    for d in sorted(tl.keys()):
        for it in tl[d]:
            if it['type'] == 'credit': balance += it['amount']
            else: balance -= it['amount']
        if balance < min_b:
            min_b = balance
            min_d = d
    print(f'  Min balance day: {min_d} balance={min_b:.4f}')
    
    # Show actual events for user
    print('  Salary events:')
    for e in sorted(evs, key=lambda x: x['settlement_date']):
        if e['category'] == 'salary':
            d = e['settlement_date']
            am = e['amount']
            st = e['status']
            desc = str(e.get('description',''))[:50]
            print(f'    {d} {am:12.4f} {st} {desc}')
    print()
