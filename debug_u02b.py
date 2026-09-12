import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import build_cash_flow_timeline, simulate_balance_90_days
from datetime import date, timedelta

data = load_data('dataset')

# request_02: GT says safe=17229139.20
# Engine says safe=17824341.09 (too high by 595201.89)
# The diff in debits is 595201.89 -- engine is projecting 595,201 LESS in debits
# So the engine is MISSING some debits

s = [x for x in data['sample_requests'] if x['request_id']=='request_02'][0]
u = s['user_id']
p = data['profiles'][u]
evs = data['events_by_user'][u]
msgs = data['messages_by_user'].get(u, [])
rdate = s['request_date']

print(f'Request date: {rdate}')
print(f'Curr bal: {p["current_available_balance"]}')
print(f'Min keep: {p["minimum_balance_to_keep"]}')

# Get timeline
tl = build_cash_flow_timeline(p, evs, msgs, rdate, days=90)

# Print engine debits by category
from collections import defaultdict
cat_debits = defaultdict(float)
for d in sorted(tl.keys()):
    for it in tl[d]:
        if it['type'] == 'debit':
            cat_debits[it.get('category','?')] += it['amount']

print('\nEngine projected debits by category (90 days):')
for cat, amt in sorted(cat_debits.items(), key=lambda x: -x[1]):
    print(f'  {cat:30} {amt:15.2f}')
print(f'  TOTAL: {sum(cat_debits.values()):20.2f}')

# Check what the actual debits in the window were vs engine
# housing events in data
housing_evs = [e for e in evs if e['category'] == 'housing']
print('\nActual housing events:')
for e in sorted(housing_evs, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    di = e['direction']
    am = e['amount']
    st = e['status']
    print(f'  {d} {di:6} {am:15.2f} {st:12}')
