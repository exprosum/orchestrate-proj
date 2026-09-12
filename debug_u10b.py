import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days
from datetime import date, timedelta

data = load_data('dataset')

# request_10: GT says safe=12700, not_affordable, not_recommended
# Engine says safe=0 (headroom=-13791.56 over 90 days)
# The GT says "Do not make this payment" - not_affordable
# But GT safe=12700... the request date is 2024-12-05
# curr_bal=750155, min_keep=225400
# Request date events: nothing on 2024-12-05 itself
# First projected debit: groceries 2024-12-05 (8011.08) - already settled
# Next: 2024-12-06 transport 5350.70

s = [x for x in data['sample_requests'] if x['request_id']=='request_10'][0]
u = s['user_id']
p = data['profiles'][u]
evs = data['events_by_user'][u]
msgs = data['messages_by_user'].get(u, [])
rdate = s['request_date']

print(f'Request date: {rdate}')
print(f'Curr bal: {p["current_available_balance"]}')
print(f'Min keep: {p["minimum_balance_to_keep"]}')

# Let me look at the balance trajectory over 90 days
tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)
balance = float(p['current_available_balance'])
print('\nDay-by-day balance (min balance tracking):')
min_b = balance
for d in sorted(tl.keys()):
    for it in tl[d]:
        if it['type'] == 'credit': balance += it['amount']
        else: balance -= it['amount']
    if balance < min_b:
        min_b = balance
        print(f'  NEW MIN: {d} balance={balance:.2f} (items: {[(x["type"],x["amount"],x.get("category","")) for x in tl[d]]})')
    
print(f'\nFinal min: {min_b:.2f}')
print(f'Min_keep: {float(p["minimum_balance_to_keep"]):.2f}')
print(f'Headroom at min: {min_b - float(p["minimum_balance_to_keep"]):.2f}')

# Now - the GT says safe=12700
# Current balance=750155, min_keep=225400
# Immediate headroom = 750155 - 225400 = 524755
# But considering next 30 days expenditures...
# Let's compute running balance and see when first it drops closest to min_keep
# while staying above it
balance = float(p['current_available_balance'])
for d in sorted(tl.keys()):
    for it in tl[d]:
        if it['type'] == 'credit': balance += it['amount']
        else: balance -= it['amount']
    if (d - rdate).days > 30:
        break
    print(f'  {d}: balance={balance:.2f} headroom={balance-float(p["minimum_balance_to_keep"]):.2f}')
