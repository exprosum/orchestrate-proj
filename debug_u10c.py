import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days
from datetime import date, timedelta

data = load_data('dataset')
s = [x for x in data['sample_requests'] if x['request_id']=='request_10'][0]
u = s['user_id']
p = data['profiles'][u]
evs = data['events_by_user'][u]
msgs = data['messages_by_user'].get(u, [])
rdate = s['request_date']

print(f'rdate: {rdate}')
print(f'curr_bal: {p["current_available_balance"]}')
print(f'min_keep: {p["minimum_balance_to_keep"]}')
print(f'GT safe: {s["amount_safe_to_pay"]}')

# User has no salary projected (gig only)
# desired_completion_date?
print(f'desired_completion_date: {s.get("desired_completion_date", "N/A")}')

# Check what the salary events look like for user_10
sal_evs = [e for e in evs if e['category'] == 'salary']
print('\nSalary events for user_10:')
for e in sorted(sal_evs, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    am = e['amount']
    st = e['status']
    desc = str(e.get('description',''))[:60]
    print(f'  {d} {am:12.2f} {st} {desc}')

# What is the request balance if user pays 12700 right now?
# balance - 12700 = 737455 > min_keep 225400 -- easily fits
# So why is 12700 "safe"? Maybe it's the leftover after immediate expenses?
# Let me check: what debits are very soon?
tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=7)
balance = float(p['current_available_balance'])
for d in sorted(tl.keys()):
    for it in tl[d]:
        if it['type'] == 'credit': balance += it['amount']
        else: balance -= it['amount']
    print(f'After {d}: balance={balance:.2f}')

# Maybe safe_to_pay = balance_after_7days - min_keep?
print(f'\nBalance after 7 days: {balance:.2f}')
print(f'Balance - min_keep: {balance - float(p["minimum_balance_to_keep"]):.2f}')
