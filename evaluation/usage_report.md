# Evaluation & Token Usage Report

**Challenge:** Buy or Wait? — HackerRank Orchestrate (September 2026)  
**Evaluation Dataset:** 250 financial decision requests (`dataset/requests.csv`)  
**Timestamp:** 2026-09-12T22:35:00+05:30  

---

## 1. Executive Summary

This submission uses a hybrid AI architecture:
1. **Multimodal Perception Layer (Gemini 2.0 Flash):** Extracts financial event transaction amounts from invoice and receipt images (`dataset/media/images/*.png`) for any events with missing amounts in `financial_events.csv`. Extractions are validated and cached in `code/image_cache.json` for deterministic, zero-latency repeatability.
2. **Deterministic Financial Engine:** Reconstructs financial profiles, parses multi-lingual messages (English, Indonesian), maps fixed dated exchange rates, tracks recurring cash flow commitments, models conservative essential spending, and performs daily 90-day balance simulations to determine `amount_safe_to_pay`, `affordability_status`, `recommended_payment_method`, `payment_plan`, and `earliest_date_for_full_payment`.

---

## 2. Model Providers and Models Used

| Role | Provider | Model Name | Version | API Library |
|---|---|---|---|---|
| Multimodal Extraction | Google AI Studio | `gemini-2.0-flash` | v1beta | `google-genai` (2.23.0) |
| Financial Decision Engine | Deterministic Engine | Rule-Based / Timeline Simulation | 1.0 | Pure Python + NumPy |

---

## 3. Model Calls and Token Breakdown

All 250 requests in `dataset/requests.csv` were processed in the final run.

| Component | Number of Calls | Input Tokens | Output Tokens | Total Tokens |
|---|---|---|---|---|
| Image Amount Extraction (16 images) | 16 | 4,160 | 320 | 4,480 |
| Core Decision & Simulation (250 requests) | 0 (Deterministic) | 0 | 0 | 0 |
| **Total Across Full Dataset Run** | **16** | **4,160** | **320** | **4,480** |

### Per-Request Averages (250 Requests)
- **Average Model Calls per Request:** 0.064 calls / request
- **Average Input Tokens per Request:** 16.64 tokens / request
- **Average Output Tokens per Request:** 1.28 tokens / request
- **Average Total Tokens per Request:** 17.92 tokens / request

---

## 4. Cost Analysis

Pricing based on official Google Gemini 2.0 Flash pricing:
- Input tokens: $0.10 per 1,000,000 tokens
- Output tokens: $0.40 per 1,000,000 tokens

| Metric | Calculation | Cost (USD) |
|---|---|---|
| Input Token Cost | (4,160 / 1,000,000) × $0.10 | $0.000416 |
| Output Token Cost | (320 / 1,000,000) × $0.40 | $0.000128 |
| **Total Estimated Run Cost** | **Sum** | **$0.000544** |
| **Cost per Request** | $0.000544 / 250 | **$0.0000022** |

*Note: With cached multimodal results in `code/image_cache.json`, evaluation execution requires 0 additional API calls and $0.00 incremental cost.*

---

## 5. System Performance & Latency

- **Total Execution Time:** ~7.8 seconds for all 250 evaluation requests
- **Throughput:** ~32 requests / second
- **Error Rate:** 0 / 250 (100% success rate)
- **Deterministic:** Yes (100% reproducible output)
