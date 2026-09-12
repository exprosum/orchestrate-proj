import sys; sys.path.insert(0, '.')
from code.data_loader import load_data
data = load_data('dataset')

for uid in ['user_02', 'user_11', 'user_10']:
    evs = data['events_by_user'][uid]
    print(f'=== {uid} events ===')
    for e in sorted(evs, key=lambda x: x['settlement_date']):
        sdate = e['settlement_date']
        direc = e['direction']
        amt = e['amount']
        cat = e['category']
        status = e['status']
        desc = str(e.get('description', ''))[:60]
        print(f'  {sdate} {direc:6} {amt:15.2f} {cat:25} {status:12} {desc}')
    print()
