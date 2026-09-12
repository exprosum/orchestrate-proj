import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days
from datetime import date, timedelta

data = load_data('dataset')

s = [x for x in data['sample_requests'] if x['request_id']=='request_02'][0]
u = s['user_id']
p = data['profiles'][u]
evs = data['events_by_user'][u]
msgs = data['messages_by_user'].get(u, [])
rdate = s['request_date']
first_inst_date = date(2025, 8, 8)
inst_amt = 15952906.67

tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)

# Simulate the actual installment plan for option_05:
# 3 payments of 15952906.67 on 2025-08-08, 2025-09-07, 2025-10-07
inst_dates = [date(2025, 8, 8), date(2025, 9, 7), date(2025, 10, 7)]
scheduled_payments = {d: inst_amt for d in inst_dates}
is_safe, min_bal, records = simulate_balance_90_days(p, tl, rdate, scheduled_payments=scheduled_payments)

print(f'With installment plan:')
print(f'  is_safe: {is_safe}')
print(f'  min_bal: {min_bal:.2f}')
print(f'  min_keep: {p["minimum_balance_to_keep"]}')
print(f'  headroom: {min_bal - float(p["minimum_balance_to_keep"]):.2f}')

# Now: what does the engine compute as amount_safe_to_pay?
# It should be the 1st installment amount that is safe
from code.financial_engine import calc_amount_safe_to_pay
engine_safe = calc_amount_safe_to_pay(p, evs, msgs, rdate, s['requested_amount'])
print(f'\nEngine safe:  {engine_safe:.2f}')
print(f'GT safe:      {s["amount_safe_to_pay"]}')
print(f'Diff:         {abs(engine_safe - s["amount_safe_to_pay"]):.2f}')

# The key question: what does the spec say amount_safe_to_pay means for installments?
# "amount_safe_to_pay is the amount safe on request_date before optional spending changes"
# "between 0 and requested_amount inclusive"
# For installments: amount_safe_to_pay = first installment amount? Or raw headroom?
# GT safe = 17229139.20, but the installment amount is 15952906.67
# 17229139.20 != 15952906.67
# So it must be the raw headroom on request_date

# Let me compute headroom on rdate directly
balance = float(p['current_available_balance'])
for d in sorted(tl.keys()):
    if d <= rdate:
        for it in tl[d]:
            if it['type'] == 'credit': balance += it['amount']
            else: balance -= it['amount']
print(f'\nBalance on rdate (after rdate items): {balance:.2f}')
print(f'Headroom on rdate: {balance - float(p["minimum_balance_to_keep"]):.2f}')

# Compute balance considering debits up to first installment minus that installment
# Then headroom = balance_before_inst - min_keep
# That's 26300139.26 (calculated above) - 29158400 = negative... 
# So that's the 90-day minimum balance with no payment

# Let's try: amount_safe_to_pay = min_balance_in_90days - min_keep (i.e., free headroom)
_, min_bal_no_pay, _ = simulate_balance_90_days(p, tl, rdate, 0.0)
print(f'\nMin balance in 90 days (no payment): {min_bal_no_pay:.2f}')
print(f'Free headroom: {min_bal_no_pay - float(p["minimum_balance_to_keep"]):.2f}')
print(f'GT safe: {s["amount_safe_to_pay"]}')
