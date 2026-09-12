import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline
from datetime import date, timedelta

data = load_data('dataset')

s = [x for x in data['sample_requests'] if x['request_id']=='request_02'][0]
u = s['user_id']
p = data['profiles'][u]
evs = data['events_by_user'][u]
msgs = data['messages_by_user'].get(u, [])
rdate = s['request_date']

tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)

# Sum actual debits that APPEAR in timeline
engine_total = sum(it['amount'] for d in tl for it in tl[d] if it['type'] == 'debit')
engine_credit = sum(it['amount'] for d in tl for it in tl[d] if it['type'] == 'credit')
print(f'Engine total debits: {engine_total:.2f}')
print(f'Engine total credits: {engine_credit:.2f}')

# GT expects safe = 17229139.20
# curr_bal = 60383889.20, min_keep = 29158400
# so GT implied: min balance during sim = 60383889.20 + credits - total_commitments >= 29158400
# => total_commitments = 60383889.20 + credits - 29158400 - 17229139.20
# But we need to think more carefully
# amount_safe_to_pay = max amount that can be paid as FIRST installment today
# For installments, the first payment is on 2025-08-08 (3 days after request)
# The installment amount is 15952906.67 (option 05)
# GT safe = 17229139.20 -- this is the headroom after accounting for upcoming expenses until first payment
# More precisely: amount_safe_to_pay means what you can pay TODAY (request_date)

# Key insight: the sim computes headroom = min_balance - min_keep over 90 days WITH payment 
# For first installment approach: pay 15952906.67 on 2025-08-08
# But amount_safe_to_pay appears to be raw headroom at rdate

# Let's compute what balance is on 2025-08-08 (day of first installment)
end_d = date(2025, 8, 8)
balance = float(p['current_available_balance'])
for d in sorted(tl.keys()):
    if d > end_d:
        break
    for it in tl[d]:
        if it['type'] == 'credit':
            balance += it['amount']
        elif it['type'] == 'debit':
            balance -= it['amount']
print(f'\nBalance on 2025-08-08 (before installment): {balance:.2f}')
print(f'Min keep: {float(p["minimum_balance_to_keep"]):.2f}')
print(f'Headroom on 2025-08-08: {balance - float(p["minimum_balance_to_keep"]):.2f}')

# Now look at what's happening before 2025-08-08
print('\nEngine timeline items before 2025-08-08:')
for d in sorted(tl.keys()):
    if d > end_d:
        break
    for it in tl[d]:
        print(f'  {d}: {it["type"]:6} {it["amount"]:15.2f} {it.get("category","")}')

# Check actual events between rdate and 2025-08-08
print('\nActual events between request_date and 2025-08-08:')
for e in sorted(evs, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    if d >= rdate and d <= end_d:
        print(f'  {d} {e["direction"]:6} {e["amount"]:15.2f} {e["category"]:25} {e["status"]}')
