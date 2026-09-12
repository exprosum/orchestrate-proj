import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days

data = load_data('dataset')
samples = {s['request_id']: s for s in data['sample_requests']}

for rid in ['request_02', 'request_11', 'request_10', 'request_12', 'request_13']:
    s = samples[rid]
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
    print(f"  GT method:  {s['recommended_payment_method']}")
    print(f"  Explanation: {s['decision_explanation'][:200]}")

    tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)
    _, min_bal, records = simulate_balance_90_days(p, tl, rdate, 0.0)
    headroom = min_bal - float(p['minimum_balance_to_keep'])
    print(f"  Engine headroom: {headroom:.2f}  min_bal: {min_bal:.2f}")
    print("  Timeline items:")
    for d in sorted(tl.keys()):
        for it in tl[d]:
            print(f"    {d}: {it['type']:6} {it['amount']:15.2f} {it.get('category','')}")
    print()
