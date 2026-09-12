import pandas as pd
from pathlib import Path
from datetime import datetime
from code.image_extractor import get_event_amount_from_image, get_image_cache

def load_data(dataset_dir: Path):
    dataset_dir = Path(dataset_dir)
    media_dir = dataset_dir / "media" / "images"

    # 1. Images mapping
    images_path = dataset_dir / "images.csv"
    images_df = pd.read_csv(images_path) if images_path.exists() else pd.DataFrame()

    # 2. Financial profiles
    profiles_df = pd.read_csv(dataset_dir / "financial_profiles.csv")
    profiles = {}
    for _, r in profiles_df.iterrows():
        uid = r["user_id"]
        profiles[uid] = {
            "user_id": uid,
            "home_currency": str(r["home_currency"]),
            "current_available_balance": float(r["current_available_balance"]),
            "minimum_balance_to_keep": float(r["minimum_balance_to_keep"]),
            "financial_priorities": str(r["financial_priorities"]).split("|") if pd.notna(r["financial_priorities"]) else [],
            "expense_categories_to_protect": str(r["expense_categories_to_protect"]).split("|") if pd.notna(r["expense_categories_to_protect"]) else [],
            "expense_categories_user_is_willing_to_reduce": str(r["expense_categories_user_is_willing_to_reduce"]).split("|") if pd.notna(r["expense_categories_user_is_willing_to_reduce"]) else [],
            "expense_categories_user_is_willing_to_stop": str(r["expense_categories_user_is_willing_to_stop"]).split("|") if pd.notna(r["expense_categories_user_is_willing_to_stop"]) else [],
            "payment_methods_user_will_consider": str(r["payment_methods_user_will_consider"]).split("|") if pd.notna(r["payment_methods_user_will_consider"]) else [],
            "max_installment_months": float(r["max_installment_months"]) if pd.notna(r["max_installment_months"]) else None,
        }

    # 3. Exchange rates
    rates_path = dataset_dir / "exchange_rates.csv"
    exchange_rates = {}
    if rates_path.exists():
        rates_df = pd.read_csv(rates_path)
        for _, r in rates_df.iterrows():
            rdate = str(r["rate_date"]).strip()
            fc = str(r["from_currency"]).strip()
            tc = str(r["to_currency"]).strip()
            rate = float(r["rate"])
            exchange_rates[(rdate, fc, tc)] = rate

    def convert_currency(amount: float, from_curr: str, to_curr: str, date_str: str) -> float:
        if from_curr == to_curr or not from_curr or not to_curr:
            return float(amount)
        # Direct lookup
        key = (date_str, from_curr, to_curr)
        if key in exchange_rates:
            return amount * exchange_rates[key]
        # Inverted lookup
        inv_key = (date_str, to_curr, from_curr)
        if inv_key in exchange_rates:
            return amount / exchange_rates[inv_key]
        # Nearest date lookup if exact date not found
        matching_rates = [k for k in exchange_rates if k[1] == from_curr and k[2] == to_curr]
        if matching_rates:
            # Pick closest date
            closest = min(matching_rates, key=lambda k: abs((datetime.strptime(k[0], "%Y-%m-%d") - datetime.strptime(date_str, "%Y-%m-%d")).days))
            return amount * exchange_rates[closest]
        print(f"Warning: No exchange rate found for {from_curr}->{to_curr} on {date_str}. Assuming 1.0")
        return float(amount)

    # 4. Financial events
    events_df = pd.read_csv(dataset_dir / "financial_events.csv")
    events_by_user = {}

    image_cache = get_image_cache()
    # Cache lookup map by event_id
    event_to_img_amount = {v["event_id"]: v["amount"] for v in image_cache.values() if "event_id" in v and "amount" in v}

    for _, r in events_df.iterrows():
        uid = r["user_id"]
        eid = r["event_id"]
        raw_amt = r["amount"]
        user_home_curr = profiles[uid]["home_currency"] if uid in profiles else str(r["currency"])

        if pd.isna(raw_amt):
            # Extract from image
            if eid in event_to_img_amount:
                raw_amt = event_to_img_amount[eid]
            else:
                try:
                    raw_amt = get_event_amount_from_image(eid, images_df, media_dir)
                except Exception as e:
                    print(f"Error loading image for event {eid}: {e}")
                    raw_amt = 0.0
        else:
            raw_amt = float(raw_amt)

        # Currency conversion if event is in foreign currency
        ev_curr = str(r["currency"]) if pd.notna(r["currency"]) else user_home_curr
        ev_sdate = str(r["settlement_date"]) if pd.notna(r["settlement_date"]) else str(r["event_date"])
        converted_amt = convert_currency(raw_amt, ev_curr, user_home_curr, ev_sdate)

        event_obj = {
            "event_id": eid,
            "user_id": uid,
            "event_type": str(r["event_type"]),
            "description": str(r["description"]),
            "category": str(r["category"]),
            "direction": str(r["direction"]),
            "amount": converted_amt,
            "original_amount": raw_amt,
            "original_currency": ev_curr,
            "currency": user_home_curr,
            "event_date": datetime.strptime(str(r["event_date"]), "%Y-%m-%d").date() if pd.notna(r["event_date"]) else None,
            "settlement_date": datetime.strptime(ev_sdate, "%Y-%m-%d").date(),
            "status": str(r["status"]).lower().strip(),
            "linked_event_id": str(r["linked_event_id"]) if pd.notna(r["linked_event_id"]) else None,
            "flexibility": str(r["flexibility"]).lower().strip() if pd.notna(r["flexibility"]) else "fixed",
            "minimum_allowed_amount": float(r["minimum_allowed_amount"]) if pd.notna(r["minimum_allowed_amount"]) else None
        }

        if uid not in events_by_user:
            events_by_user[uid] = []
        events_by_user[uid].append(event_obj)

    # 5. Messages
    messages_path = dataset_dir / "messages.csv"
    messages_by_user = {}
    if messages_path.exists():
        msg_df = pd.read_csv(messages_path)
        for _, r in msg_df.iterrows():
            uid = r["user_id"]
            msg_obj = {
                "message_id": str(r["message_id"]),
                "user_id": uid,
                "request_id": str(r["request_id"]) if pd.notna(r["request_id"]) else None,
                "related_event_id": str(r["related_event_id"]) if pd.notna(r["related_event_id"]) else None,
                "sent_at": str(r["sent_at"]),
                "source_type": str(r["source_type"]),
                "message_text": str(r["message_text"])
            }
            if uid not in messages_by_user:
                messages_by_user[uid] = []
            messages_by_user[uid].append(msg_obj)

    # 6. Payment options
    options_path = dataset_dir / "request_payment_options.csv"
    options_by_request = {}
    if options_path.exists():
        opt_df = pd.read_csv(options_path)
        for _, r in opt_df.iterrows():
            req_id = r["request_id"]
            opt_obj = {
                "payment_option_id": str(r["payment_option_id"]),
                "request_id": req_id,
                "payment_method": str(r["payment_method"]),
                "payment_amount": float(r["payment_amount"]),
                "number_of_payments": int(r["number_of_payments"]),
                "first_payment_date": datetime.strptime(str(r["first_payment_date"]), "%Y-%m-%d").date(),
                "payment_frequency_days": int(r["payment_frequency_days"]) if pd.notna(r["payment_frequency_days"]) else 0,
                "financing_fee": float(r["financing_fee"]) if pd.notna(r["financing_fee"]) else 0.0,
                "total_payable_amount": float(r["total_payable_amount"])
            }
            if req_id not in options_by_request:
                options_by_request[req_id] = []
            options_by_request[req_id].append(opt_obj)

    # 7. Requests
    requests_path = dataset_dir / "requests.csv"
    requests_list = []
    if requests_path.exists():
        req_df = pd.read_csv(requests_path)
        for _, r in req_df.iterrows():
            requests_list.append({
                "request_id": str(r["request_id"]),
                "user_id": str(r["user_id"]),
                "request_date": datetime.strptime(str(r["request_date"]), "%Y-%m-%d").date(),
                "request_type": str(r["request_type"]),
                "requested_amount": float(r["requested_amount"]),
                "desired_completion_date": datetime.strptime(str(r["desired_completion_date"]), "%Y-%m-%d").date(),
                "allows_partial_payment": str(r["allows_partial_payment"]).lower() in ["true", "1", "t"],
                "request_text": str(r["request_text"])
            })

    # 8. Sample requests
    samples_path = dataset_dir / "sample_requests.csv"
    sample_requests_list = []
    if samples_path.exists():
        sample_df = pd.read_csv(samples_path)
        for _, r in sample_df.iterrows():
            sample_requests_list.append({
                "request_id": str(r["request_id"]),
                "user_id": str(r["user_id"]),
                "request_date": datetime.strptime(str(r["request_date"]), "%Y-%m-%d").date(),
                "request_type": str(r["request_type"]),
                "requested_amount": float(r["requested_amount"]),
                "desired_completion_date": datetime.strptime(str(r["desired_completion_date"]), "%Y-%m-%d").date(),
                "allows_partial_payment": str(r["allows_partial_payment"]).lower() in ["true", "1", "t"],
                "request_text": str(r["request_text"]),
                "amount_safe_to_pay": float(r["amount_safe_to_pay"]),
                "affordability_status": str(r["affordability_status"]),
                "recommended_payment_method": str(r["recommended_payment_method"]),
                "payment_plan": str(r["payment_plan"]),
                "earliest_date_for_full_payment": datetime.strptime(str(r["earliest_date_for_full_payment"]), "%Y-%m-%d").date() if pd.notna(r["earliest_date_for_full_payment"]) and str(r["earliest_date_for_full_payment"]).strip() != "" and str(r["earliest_date_for_full_payment"]) != "nan" else None,
                "spending_changes_needed": str(r["spending_changes_needed"]),
                "decision_explanation": str(r["decision_explanation"])
            })

    return {
        "profiles": profiles,
        "events_by_user": events_by_user,
        "messages_by_user": messages_by_user,
        "options_by_request": options_by_request,
        "requests": requests_list,
        "sample_requests": sample_requests_list,
        "convert_currency": convert_currency
    }
