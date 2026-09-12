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

# GT safe = 12700, not_affordable
# Desired deadline: 2025-02-10
# The GT says NOT AFFORDABLE - meaning they cannot safely pay 266700 with available options
# But what does 12700 represent?
# min installment = 19558/month, but GT says can't afford even that
# safe = 12700 - this MIGHT be: 
#   minimum of (headroom at all installment payment dates WITH payment)
# OR it might just be: some fraction of the installment amount
# Let me check installment payment dates:
# Option 28: 19558 per month starting 2024-12-13, every 30 days, 15 payments
# Dates: 2024-12-13, 2025-01-12, 2025-02-11...
# If user pays 19558 on 2024-12-13:
# Balance before payment on 12-13 = 705266.72 (from debug_u10b)
# After payment: 705266.72 - 19558 = 685708.72
# If then paying 19558 on 2025-01-12:
# Balance before 01-12 = 521914.52 - 19558 = 502356.52 (safe!)
# If then on 2025-02-11: Balance before = ~344000 - 19558 = ~324000 (safe)

# So installment IS affordable... but the min balance over 90 days AFTER all installments?
tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)
# Try installment plan option 28
inst_dates = [date(2024, 12, 13) + timedelta(days=30*i) for i in range(15)]
inst_dates = [d for d in inst_dates if d <= rdate + timedelta(days=90)]
print('Installment dates in 90 days:', inst_dates)
inst_payments = {d: 19558.0 for d in inst_dates}
is_safe, min_bal, records = simulate_balance_90_days(p, tl, rdate, scheduled_payments=inst_payments)
min_keep = float(p['minimum_balance_to_keep'])
print(f'With installment plan:')
print(f'  is_safe: {is_safe}')
print(f'  min_bal: {min_bal:.2f}')
print(f'  headroom: {min_bal - min_keep:.2f}')
print()

# Check how headroom deteriorates when we try diff amounts
for candidate_safe in [0, 5000, 10000, 12700, 13000, 15000, 19558, 20000]:
    payments = {inst_dates[0]: candidate_safe}
    _, mb, _ = simulate_balance_90_days(p, tl, rdate, scheduled_payments=payments)
    print(f'  pay {candidate_safe:8.0f}: min_bal={mb:.2f} headroom={mb-min_keep:.2f}')
