import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
from datetime import date, timedelta

data = load_data('dataset')

# Look at user_02 near request date
evs = data['events_by_user']['user_02']
rdate = date(2025, 8, 5)
recent = sorted(evs, key=lambda x: x['settlement_date'])
print('Events around request date for user_02:')
for e in recent:
    diff = abs((e['settlement_date'] - rdate).days)
    if diff < 90:
        d = e['settlement_date']
        di = e['direction']
        am = e['amount']
        ca = e['category']
        st = e['status']
        desc = str(e.get('description', ''))[:50]
        print(f'  {d} {di:6} {am:15.2f} {ca:25} {st:12} {desc}')
        
print()
print('User_02 salary events only:')
for e in sorted(evs, key=lambda x: x['settlement_date']):
    if e['category'] == 'salary':
        d = e['settlement_date']
        di = e['direction']
        am = e['amount']
        st = e['status']
        desc = str(e.get('description', ''))[:50]
        print(f'  {d} {di:6} {am:15.2f} {st:12} {desc}')
