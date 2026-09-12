import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days
from datetime import date, timedelta
from collections import defaultdict

data = load_data('dataset')

# USER_12: request_12
# Salary: Nov 55846, Dec 41904, Jan 61315 (all 2025-2026 "Seasonal contract")
# Request date: 2026-04-05 -- no upcoming salary projected
# GT safe = 65164 (full requested amount)
# Engine safe = 57204 (7960 less)
# The engine is missing projected salary for April 2026!

s = [x for x in data['sample_requests'] if x['request_id']=='request_12'][0]
u = s['user_id']
p = data['profiles'][u]
evs = data['events_by_user'][u]
msgs = data['messages_by_user'].get(u, [])
rdate = s['request_date']

print('=== user_12 === ')
print(f'Request date: {rdate}')

# Check messages for user_12
for m in msgs:
    print(f'  Message: {m}')

# Look at all events
print('\nAll events (sorted by date):')
for e in sorted(evs, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    di = e['direction']
    am = e['amount']
    ca = e['category']
    st = e['status']
    desc = str(e.get('description',''))[:50]
    print(f'  {d} {di:6} {am:12.2f} {ca:25} {st:12} {desc}')

# Check if there are any scheduled events
scheduled = [e for e in evs if e['status'] in ['scheduled', 'pending']]
print(f'\nScheduled/Pending events: {len(scheduled)}')
for e in scheduled:
    d = e['settlement_date']
    di = e['direction']
    am = e['amount']
    ca = e['category']
    st = e['status']
    print(f'  {d} {di:6} {am:12.2f} {ca:25} {st}')
    
# The GT says: "Use 3 installments starting April 19, 2026"
# But GT safe = 65164 = full amount. So why isn't engine computing full amount?
# Maybe the GT considers some income that engine doesn't
print(f'\nEngine headroom: {57204.15:.2f}')
print(f'GT safe:        {s["amount_safe_to_pay"]:.2f}')
print(f'Diff:           {abs(57204.15 - s["amount_safe_to_pay"]):.2f}')
