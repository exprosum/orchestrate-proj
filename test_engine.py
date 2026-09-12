import sys
sys.path.insert(0, '.')
from code.data_loader import load_data
from code.financial_engine import calc_amount_safe_to_pay, calc_earliest_full_payment_date

data = load_data('dataset')
profiles = data['profiles']
events = data['events_by_user']
messages = data['messages_by_user']
samples = data['sample_requests']

print(f"=== EVALUATING ON {len(samples)} SAMPLES ===")
safe_diffs = []
date_matches = 0

for s in samples:
    u = s['user_id']
    req_amt = s['requested_amount']
    rdate = s['request_date']
    user_p = profiles[u]
    user_e = events.get(u, [])
    user_m = messages.get(u, [])

    pred_safe = calc_amount_safe_to_pay(user_p, user_e, user_m, rdate, req_amt)
    gt_safe = s['amount_safe_to_pay']

    pred_date = calc_earliest_full_payment_date(user_p, user_e, user_m, rdate, req_amt)
    gt_date = s['earliest_date_for_full_payment']

    diff_safe = abs(pred_safe - gt_safe)
    safe_diffs.append(diff_safe)
    date_match = (pred_date == gt_date)
    if date_match:
        date_matches += 1

    status_icon = "OK" if diff_safe < 5.0 and date_match else "DIFF"
    print(f"{s['request_id']} | {status_icon:4s} | safe: pred={pred_safe:12.2f} vs gt={gt_safe:12.2f} (diff={diff_safe:8.2f}) | date: pred={str(pred_date):10s} vs gt={str(gt_date):10s}")

print(f"\nMean Absolute Error on safe amount: {sum(safe_diffs)/len(safe_diffs):.2f}")
print(f"Earliest Date Accuracy: {date_matches}/{len(samples)} ({date_matches/len(samples)*100:.1f}%)")
