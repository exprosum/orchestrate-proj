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

# desired_completion_date = 2025-02-10
# The GT says NOT affordable. Safe=12700. Let's figure this out.
# Maybe the 12700 = safe amount means: considering the installment plan
# installment option 28: 19558 per month for 15 months starting 2024-12-13
# If we simulate: can they pay 12700 now and still be safe?
# Or maybe safe=12700 is computed as: headroom at the TIGHTEST month-end point

# Check specifically: what is the balance at the DEADLINE (2025-02-10)?
tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)
deadline = date(2025, 2, 10)
balance = float(p['current_available_balance'])
min_keep = float(p['minimum_balance_to_keep'])
min_b = balance
for d in sorted(tl.keys()):
    if d > deadline:
        break
    for it in tl[d]:
        if it['type'] == 'credit': balance += it['amount']
        else: balance -= it['amount']
    if balance < min_b: min_b = balance

print(f'Balance at deadline (2025-02-10): {balance:.2f}')
print(f'Min balance up to deadline: {min_b:.2f}')
print(f'Headroom at deadline: {balance - min_keep:.2f}')
print(f'Min headroom up to deadline: {min_b - min_keep:.2f}')
print(f'GT safe: {s["amount_safe_to_pay"]}')

# Try: what is the safe amount if we compute headroom at end of desired_completion_date?
# Maybe it's: balance_at_deadline - min_keep
# = balance_at_deadline - 225400
# If balance_at_deadline = 238100, then safe = 12700

# Or maybe: salary IS included but at a conservative rate
# Looking at gig earnings in the dataset: ~60000-80000/week
# Avg weekly earning = ~66000
# Over 90 days (13 weeks) = ~858000 extra income
# With that income included in 90-day sim would change things...

# Let me think about "amount_safe_to_pay" for not_affordable:
# The spec says: amount_safe_to_pay is between 0 and requested_amount
# For not_affordable: amount_safe_to_pay could be the maximum partial you could pay
# i.e., the headroom at request_date itself
# curr_bal - min_keep - PENDING_DEBITS_TODAY = 750155 - 225400 - X = 12700
# => X = 512055
# That seems too high for same-day debits

# Maybe: maybe the engine is correct that 0 should be the safe amount
# and GT safe=12700 is some other logic. Let me check:
# Perhaps amount_safe = headroom at request_date minus NEXT INSTALLMENT PAYMENT
# If installment = 19558/month, and headroom at deadline = some value...

# Actually let me look at the minimum balance BETWEEN request_date and desired_completion_date
# and find headroom above min_keep
print('\n--- Balance trajectory to deadline ---')
balance = float(p['current_available_balance'])
for d in sorted(tl.keys()):
    if d > deadline:
        break
    prev_bal = balance
    for it in tl[d]:
        if it['type'] == 'credit': balance += it['amount']
        else: balance -= it['amount']
    h = balance - min_keep
    if d >= date(2025, 1, 15):
        items_str = [(x['type'], x['amount'], x.get('category','')) for x in tl[d]]
        print(f'  {d}: bal={balance:.2f} headroom={h:.2f} | {items_str}')
