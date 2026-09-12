import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set

def parse_user_messages(messages: List[dict], user_id: str, request_date) -> dict:
    """
    Parse messages for user to extract salary changes, rent changes, contract terminations, etc.
    """
    amendments = {
        "salary_amount": None,
        "salary_date": None,
        "salary_terminated": False,
        "one_time_income": [], # list of (date, amount)
        "rent_multiplier": 1.0,
        "confirmed_invoices": [], # list of (date, amount)
    }

    # Sort messages by sent_at
    sorted_msgs = sorted(messages, key=lambda m: m.get("sent_at", ""))

    for msg in sorted_msgs:
        txt = msg.get("message_text", "")
        src = msg.get("source_type", "")

        # 1. Salary termination / seasonal contract ended
        if "seasonal contract has ended" in txt.lower() or "no off-season income" in txt.lower():
            amendments["salary_terminated"] = True

        # 2. Salary amount change
        # Indonesian: "Gaji bulanan Anda naik menjadi IDR 42750000" or "Gaji pokok yang dikonfirmasi adalah IDR 38760000"
        m_idr = re.search(r"(?:Gaji bulanan Anda naik menjadi|Gaji pokok yang dikonfirmasi adalah)\s*(?:IDR)?\s*([\d\.,]+)", txt, re.IGNORECASE)
        if m_idr:
            amt = float(m_idr.group(1).replace(".", "").replace(",", ""))
            amendments["salary_amount"] = amt

        # English: "temporary monthly pay is EUR 1037.52" or "next salary is reduced to EUR 1422.85" or "first salary will be EUR 1661"
        # or "Regular salary of EUR 2717 resumes" or "regular salary for the next payroll is EUR 1452"
        m_eng = re.search(r"(?:temporary monthly pay is|next salary is reduced to|first salary will be|regular salary of|regular salary for the next payroll is)\s*[A-Z]{3}\s*([\d\.,]+)", txt, re.IGNORECASE)
        if m_eng:
            raw_val = m_eng.group(1).rstrip(".").rstrip(",").replace(",", "")
            amt = float(raw_val)
            amendments["salary_amount"] = amt

        # 3. Salary date change
        # "Your confirmed salary is now expected on 2024-09-23" or "confirmed credit date is 2026-01-15" or "Perubahan ini berlaku mulai 2025-08-15"
        m_date = re.search(r"(?:expected on|confirmed credit date is|berlaku mulai|resumes on)\s*(\d{4}-\d{2}-\d{2})", txt, re.IGNORECASE)
        if m_date:
            d_str = m_date.group(1)
            try:
                amendments["salary_date"] = datetime.strptime(d_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        # 4. One-time arrears adjustment
        # "one-time arrears adjustment of EUR 653.40"
        m_arr = re.search(r"one-time arrears adjustment of\s*[A-Z]{3}\s*([\d\.,]+)", txt, re.IGNORECASE)
        if m_arr:
            raw_val = m_arr.group(1).rstrip(".").rstrip(",").replace(",", "")
            amt = float(raw_val)
            # applies on next salary date
            s_date = amendments["salary_date"] or (request_date + timedelta(days=15) if request_date else None)
            if s_date:
                amendments["one_time_income"].append((s_date, amt))

        # 5. Rent increase
        # "increases monthly rent by 12%"
        m_rent = re.search(r"increases monthly rent by\s*(\d+)%", txt, re.IGNORECASE)
        if m_rent:
            pct = float(m_rent.group(1))
            amendments["rent_multiplier"] = 1.0 + pct / 100.0

        # 6. Freelance / invoice confirmed
        # "Klien menyetujui pembayaran faktur sebesar IDR 30780000. Penyelesaian diperkirakan pada 2025-08-15"
        # "client approved an invoice payment of INR 196000. Settlement is expected on 2024-12-15"
        m_inv = re.search(r"(?:pembayaran faktur sebesar|invoice payment of)\s*[A-Z]{3}\s*([\d\.,]+).*?(?:Penyelesaian diperkirakan pada|Settlement is expected on)\s*(\d{4}-\d{2}-\d{2})", txt, re.IGNORECASE | re.DOTALL)
        if m_inv:
            inv_amt = float(m_inv.group(1).replace(".", "").replace(",", ""))
            inv_date = datetime.strptime(m_inv.group(2), "%Y-%m-%d").date()
            amendments["confirmed_invoices"].append((inv_date, inv_amt))

    return amendments
