import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days, calc_amount_safe_to_pay
from datetime import date, timedelta

data = load_data('dataset')

# request_10: engine gives 0 but GT says 12700 
# Note: GT says status=not_affordable, method=not_recommended
# So why is GT safe 12700?
s10 = [x for x in data['sample_requests'] if x['request_id']=='request_10'][0]
print('request_10:')
print(f'  GT safe: {s10["amount_safe_to_pay"]}')
print(f'  Req amt: {s10["requested_amount"]}')
print(f'  Status:  {s10["affordability_status"]}')
print(f'  Method:  {s10["recommended_payment_method"]}')
print(f'  GT date: {s10["earliest_date_for_full_payment"]}')
print(f'  Explanation: {s10["decision_explanation"][:300]}')

u10 = s10['user_id']
p10 = data['profiles'][u10]
evs10 = data['events_by_user'][u10]
msgs10 = data['messages_by_user'].get(u10, [])
rdate10 = s10['request_date']

tl10 = build_cash_flow_timeline(p10, evs10, msgs10, rdate10, days=90)
_, min_bal10, _ = simulate_balance_90_days(p10, tl10, rdate10, 0.0)
headroom10 = min_bal10 - float(p10['minimum_balance_to_keep'])
print(f'\n  Engine headroom: {headroom10:.2f}  (min_bal={min_bal10:.2f})')
engine_safe10 = calc_amount_safe_to_pay(p10, evs10, msgs10, rdate10, s10['requested_amount'])
print(f'  Engine safe: {engine_safe10:.2f}')

# The GT safe=12700, note=not_affordable
# This means on request_date, the user can SAFELY set aside 12700 
# but CANNOT afford the full 266700
# The engine gives 0 (says can't safely pay anything) but GT says 12700
# Let me check: curr_bal=750155, min_keep=225400, diff=524755
# But engine headroom is NEGATIVE over 90 days meaning some future expense dips below min_keep
# So why does GT say safe=12700?

# Maybe: amount_safe_to_pay is assessed at request_date point in time, not min over 90 days
# At request_date: balance=750155, min_keep=225400, direct headroom=524755
# But GT says safe=12700... That's way less
# Maybe it's considering some pending or scheduled debit very soon
print()
print('  Events near request_date:')
for e in sorted(evs10, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    rdate10_d = rdate10 if isinstance(rdate10, date) else date.fromisoformat(str(rdate10))
    diff = (d - rdate10_d).days
    if -5 <= diff <= 15:
        di = e['direction']
        am = e['amount']
        ca = e['category']
        st = e['status']
        print(f'    {d} {di:6} {am:15.2f} {ca:25} {st}')
        
# Check payment options for request_10
print('\nPayment options for request_10:')
for opt in data['options_by_request'].get('request_10', []):
    print(f'  {opt}')
