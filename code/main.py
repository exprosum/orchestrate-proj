"""
Buy or Wait? — Main entry point
HackerRank Orchestrate September 2026

Run:
    python code/main.py

Requires:
    GEMINI_API_KEY environment variable (or .env file in project root)
"""

import sys
import os
import csv
import traceback
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

# Load .env from project root
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to sys.path so "code.*" imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from code.data_loader import load_data
from code.financial_engine import (
    build_cash_flow_timeline,
    simulate_balance_90_days,
    calc_amount_safe_to_pay,
    calc_earliest_full_payment_date,
)

# ─────────────────────────────────────────
# Constants
# ─────────────────────────────────────────
DATASET_DIR = Path(__file__).parent.parent / "dataset"
OUTPUT_PATH = Path(__file__).parent.parent / "output.csv"
OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]


# ─────────────────────────────────────────
# Payment option helpers
# ─────────────────────────────────────────

def _is_installment_method(method: str) -> bool:
    return method.lower() in ("installments", "installment", "bnpl")


def _user_accepts_method(user_profile: dict, method: str) -> bool:
    """Return True if the user's payment preferences allow this method."""
    prefs = [p.lower().strip() for p in user_profile.get("payment_methods_user_will_consider", [])]
    if not prefs:
        return True  # no restrictions stated
    method_lc = method.lower().strip()
    for p in prefs:
        if method_lc in p or p in method_lc:
            return True
    return False


def _installment_plan_ok(user_profile: dict, option: dict) -> bool:
    """Return True if this installment option is compatible with user preferences."""
    max_months = user_profile.get("max_installment_months")
    if max_months is None:
        return False  # user will not consider installments
    num_payments = option.get("number_of_payments", 0)
    freq_days = option.get("payment_frequency_days", 30)
    approx_months = (num_payments * freq_days) / 30
    return approx_months <= max_months


def _build_installment_payment_schedule(option: dict) -> list:
    """Build a list of (date, amount) for an installment option."""
    schedule = []
    first_date = option["first_payment_date"]
    n = option["number_of_payments"]
    amt_each = round(option["payment_amount"], 2)
    freq = option.get("payment_frequency_days", 30)
    for i in range(n):
        pdate = first_date + timedelta(days=freq * i)
        schedule.append((pdate, amt_each))
    return schedule


def _check_installment_safe(
    user_profile: dict,
    timeline: dict,
    request_date: date,
    schedule: list,
) -> bool:
    """Simulate balance with installment schedule and check if always >= min_keep."""
    scheduled_payments = {pdate: amt for pdate, amt in schedule}
    is_safe, _, _ = simulate_balance_90_days(
        user_profile, timeline, request_date,
        initial_payment=0.0, scheduled_payments=scheduled_payments
    )
    return is_safe


def _format_plan(schedule: list) -> str:
    """Format [(date, amount)] as YYYY-MM-DD:amount|..."""
    return "|".join(f"{d.strftime('%Y-%m-%d')}:{a:.2f}" for d, a in sorted(schedule))


# ─────────────────────────────────────────
# Spending changes helpers
# ─────────────────────────────────────────

def _try_spending_changes(
    user_profile: dict,
    user_events: list,
    user_messages: list,
    request_date: date,
    requested_amount: float,
    desired_completion_date: date,
) -> tuple:
    """
    Try to find spending changes that make the full payment affordable today.
    Returns (spending_changes_list, new_safe_amount) or ([], 0.0) if not possible.
    """
    stoppable = set(user_profile.get("expense_categories_user_is_willing_to_stop", []))
    reducible = set(user_profile.get("expense_categories_user_is_willing_to_reduce", []))
    protected = set(user_profile.get("expense_categories_to_protect", []))

    # Collect flexible, non-protected future events
    flexible_debits = []
    for e in user_events:
        if (
            e["direction"] == "debit"
            and e["flexibility"] in ("flexible", "adjustable")
            and e["category"] not in protected
            and e["settlement_date"] >= request_date
            and e["settlement_date"] <= request_date + timedelta(days=90)
            and e["status"] in ("pending", "scheduled", "settled")
        ):
            flexible_debits.append(e)

    candidate_changes = []
    for e in flexible_debits:
        if e["category"] in stoppable:
            candidate_changes.append(f"stop:{e['event_id']}")
        elif e["category"] in reducible and e.get("minimum_allowed_amount") is not None:
            min_amt = e["minimum_allowed_amount"]
            candidate_changes.append(f"reduce_to:{e['event_id']}:{min_amt:.2f}")

    if not candidate_changes:
        return [], 0.0

    # Try up to 3 changes greedily
    applied = []
    for change in candidate_changes:
        if len(applied) >= 3:
            break
        test_changes = applied + [change]
        safe_amt = calc_amount_safe_to_pay(
            user_profile, user_events, user_messages, request_date, requested_amount,
            spending_changes=test_changes
        )
        if safe_amt >= requested_amount - 1e-4:
            applied.append(change)
            return applied, safe_amt
        applied.append(change)

    safe_amt = calc_amount_safe_to_pay(
        user_profile, user_events, user_messages, request_date, requested_amount,
        spending_changes=applied
    )
    return applied, safe_amt


# ─────────────────────────────────────────
# Core decision function
# ─────────────────────────────────────────

def decide_request(
    request: dict,
    user_profile: dict,
    user_events: list,
    user_messages: list,
    payment_options: list,
) -> dict:
    req_id = request["request_id"]
    req_date = request["request_date"]
    req_amt = float(request["requested_amount"])
    desired_date = request["desired_completion_date"]
    allows_partial = request.get("allows_partial_payment", False)
    home_curr = user_profile.get("home_currency", "")

    # Step 1: Amount safe to pay today (no spending changes)
    safe_today = calc_amount_safe_to_pay(
        user_profile, user_events, user_messages, req_date, req_amt
    )

    # Step 2: Earliest full payment date
    earliest_full_date = calc_earliest_full_payment_date(
        user_profile, user_events, user_messages, req_date, req_amt, desired_date
    )

    # Step 3: Build timeline for installment checks
    timeline = build_cash_flow_timeline(
        user_profile, user_events, user_messages, req_date, days=90
    )

    # Step 4: Affordable right now?
    if safe_today >= req_amt - 1e-4:
        return _build_output(
            req_id=req_id,
            safe_today=req_amt,
            status="affordable_now",
            method="full_payment",
            plan=f"{req_date.strftime('%Y-%m-%d')}:{req_amt:.2f}",
            earliest_full=req_date,
            changes="none",
            explanation=(
                f"Current balance covers {home_curr} {req_amt:.2f} in full on {req_date} "
                f"while staying above the minimum balance. Full payment recommended."
            ),
        )

    # Step 5: Check installment options
    best_installment = None
    for opt in payment_options:
        method = opt.get("payment_method", "").lower()
        if not _is_installment_method(method):
            continue
        if not _user_accepts_method(user_profile, method):
            continue
        if not _installment_plan_ok(user_profile, opt):
            continue
        schedule = _build_installment_payment_schedule(opt)
        if schedule and schedule[-1][0] > desired_date:
            continue  # plan misses deadline
        if _check_installment_safe(user_profile, timeline, req_date, schedule):
            best_installment = (opt, schedule)
            break

    if best_installment:
        opt, schedule = best_installment
        # For affordable_with_plan via installments, amount_safe_to_pay = requested_amount
        # (the full purchase amount is being committed to via the plan)
        return _build_output(
            req_id=req_id,
            safe_today=req_amt,
            status="affordable_with_plan",
            method="installments",
            plan=_format_plan(schedule),
            earliest_full=earliest_full_date,
            changes="none",
            explanation=(
                f"Use {opt['number_of_payments']} installments of "
                f"{home_curr} {opt['payment_amount']:.2f}, "
                f"starting {schedule[0][0].strftime('%Y-%m-%d')}. "
                f"This keeps the balance above the minimum required."
            ),
        )

    # Step 6: Partial payment?
    if allows_partial and 0 < safe_today < req_amt - 1e-4:
        if earliest_full_date and earliest_full_date <= desired_date:
            remaining = round(req_amt - safe_today, 2)
            plan_str = (
                f"{req_date.strftime('%Y-%m-%d')}:{safe_today:.2f}|"
                f"{earliest_full_date.strftime('%Y-%m-%d')}:{remaining:.2f}"
            )
            return _build_output(
                req_id=req_id,
                safe_today=safe_today,
                status="affordable_with_plan",
                method="partial_payment",
                plan=plan_str,
                earliest_full=earliest_full_date,
                changes="none",
                explanation=(
                    f"Can pay {home_curr} {safe_today:.2f} today and "
                    f"the remaining {home_curr} {remaining:.2f} on {earliest_full_date}, "
                    f"completing by the deadline of {desired_date}."
                ),
            )

    # Step 7: Spending changes?
    changes_list, safe_with_changes = _try_spending_changes(
        user_profile, user_events, user_messages, req_date, req_amt, desired_date
    )

    if changes_list and safe_with_changes >= req_amt - 1e-4:
        return _build_output(
            req_id=req_id,
            safe_today=safe_today,
            status="affordable_with_plan",
            method="full_payment",
            plan=f"{req_date.strftime('%Y-%m-%d')}:{req_amt:.2f}",
            earliest_full=req_date,
            changes="|".join(changes_list),
            explanation=(
                f"Full payment of {home_curr} {req_amt:.2f} becomes feasible after "
                f"recommended spending adjustments. Changes: {'; '.join(changes_list)}."
            ),
        )

    # Step 8: Pay later?
    if earliest_full_date:
        if earliest_full_date <= desired_date:
            return _build_output(
                req_id=req_id,
                safe_today=safe_today,
                status="affordable_later",
                method="wait",
                plan="none",
                earliest_full=earliest_full_date,
                changes="none",
                explanation=(
                    f"Cannot safely pay {home_curr} {req_amt:.2f} today "
                    f"(safe today: {home_curr} {safe_today:.2f}). "
                    f"Earliest safe full payment date: {earliest_full_date}, "
                    f"within deadline of {desired_date}. Recommend waiting."
                ),
            )
        else:
            return _build_output(
                req_id=req_id,
                safe_today=safe_today,
                status="not_affordable",
                method="not_recommended",
                plan="none",
                earliest_full=earliest_full_date,
                changes="none",
                explanation=(
                    f"Cannot safely pay {home_curr} {req_amt:.2f} by the deadline of {desired_date}. "
                    f"The earliest forecast date for full payment is {earliest_full_date}, "
                    f"which is after the desired completion date."
                ),
            )

    # Step 9: Not affordable in forecast window
    return _build_output(
        req_id=req_id,
        safe_today=safe_today,
        status="not_affordable",
        method="not_recommended",
        plan="none",
        earliest_full=None,
        changes="none",
        explanation=(
            f"Cannot safely pay {home_curr} {req_amt:.2f}. "
            f"Safe amount today: {home_curr} {safe_today:.2f}. "
            f"No safe full payment date found within the 90-day forecast window."
        ),
    )


def _build_output(
    req_id: str,
    safe_today: float,
    status: str,
    method: str,
    plan: str,
    earliest_full: Optional[date],
    changes: str,
    explanation: str,
) -> dict:
    return {
        "request_id": req_id,
        "amount_safe_to_pay": round(safe_today, 2),
        "affordability_status": status,
        "recommended_payment_method": method,
        "payment_plan": plan,
        "earliest_date_for_full_payment": earliest_full.strftime("%Y-%m-%d") if earliest_full else "",
        "spending_changes_needed": changes,
        "decision_explanation": explanation,
    }


# ─────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────

def main():
    print("=" * 60)
    print("Buy or Wait? — HackerRank Orchestrate September 2026")
    print("=" * 60)

    print(f"\nLoading data from {DATASET_DIR} ...")
    data = load_data(DATASET_DIR)

    profiles = data["profiles"]
    events_by_user = data["events_by_user"]
    messages_by_user = data["messages_by_user"]
    options_by_request = data["options_by_request"]
    requests = data["requests"]

    print(f"  Profiles:          {len(profiles)}")
    print(f"  Requests:          {len(requests)}")
    print(f"  Users with events: {len(events_by_user)}")

    results = []
    failed = 0

    for i, req in enumerate(requests, 1):
        req_id = req["request_id"]
        user_id = req["user_id"]

        user_profile = profiles.get(user_id)
        if not user_profile:
            print(f"  [{i:3d}/{len(requests)}] WARNING: No profile for user {user_id} ({req_id})")
            failed += 1
            results.append({
                "request_id": req_id,
                "amount_safe_to_pay": 0.0,
                "affordability_status": "not_affordable",
                "recommended_payment_method": "not_recommended",
                "payment_plan": "none",
                "earliest_date_for_full_payment": "",
                "spending_changes_needed": "none",
                "decision_explanation": "User profile not found.",
            })
            continue

        user_events = events_by_user.get(user_id, [])
        user_messages = messages_by_user.get(user_id, [])
        payment_options = options_by_request.get(req_id, [])

        try:
            result = decide_request(
                request=req,
                user_profile=user_profile,
                user_events=user_events,
                user_messages=user_messages,
                payment_options=payment_options,
            )
            results.append(result)
        except Exception as e:
            failed += 1
            print(f"  [{i:3d}/{len(requests)}] ERROR on {req_id}: {e}")
            traceback.print_exc()
            results.append({
                "request_id": req_id,
                "amount_safe_to_pay": 0.0,
                "affordability_status": "not_affordable",
                "recommended_payment_method": "not_recommended",
                "payment_plan": "none",
                "earliest_date_for_full_payment": "",
                "spending_changes_needed": "none",
                "decision_explanation": f"Processing error: {str(e)[:200]}",
            })

        if i % 50 == 0 or i == len(requests):
            print(f"  Processed {i}/{len(requests)} requests ({failed} errors)")

    # Write output
    print(f"\nWriting {len(results)} rows to {OUTPUT_PATH} ...")
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"Done! Output: {OUTPUT_PATH}")
    print(f"  Total: {len(results)} | Errors: {failed}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
