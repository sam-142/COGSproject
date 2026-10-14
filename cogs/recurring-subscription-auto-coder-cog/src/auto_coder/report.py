"""Write results: the QuickBooks file, a review CSV for accounting, the full JSON,
and a terminal summary."""
import csv
import json
from pathlib import Path

from auto_coder.coding import QB_COLUMNS
from cog_transactions.shape import to_json

# The order labels appear in the review file and summary: what needs a look first.
SHOWN = ["amount-changed", "new", "likely-recurring", "recurring"]

REVIEW_COLUMNS = [
    "label", "quickbooks", "review", "vendor", "merchant_name", "merchant_descriptor",
    "amount", "currency", "change_vs_last", "transaction_date", "status", "card_last4", "cardholder",
    "account", "account_from", "class", "department", "blank_fields",
    "months_seen", "reason", "transaction_id",
]


def _change_text(change):
    if not change or change["change_percent"] is None:
        return ""
    return f"{change['change_percent']:+g}% vs {change['last_amount']:.2f} ({change['month']})"


def _review_rows(result):
    rows = []
    for tx in result["transactions"]:
        rec, cod, p = tx["inferred"]["recurrence"], tx["inferred"]["coding"], tx["parsed"]
        if rec["label"] not in SHOWN:
            continue
        entry, sources = cod.get("entry", {}), cod.get("from", {})
        rows.append({
            "label": rec["label"],
            "quickbooks": cod["status"],
            "review": cod.get("review") or "",
            "vendor": tx["inferred"]["vendor"]["id"],
            "merchant_name": p["merchant_name"] or "",
            "merchant_descriptor": p["merchant_descriptor"],
            "amount": f"{p['amount']:.2f}",
            "currency": p["currency"],
            "change_vs_last": _change_text(rec["evidence"]["vs_last_charge"]),
            "transaction_date": p["transaction_date"].isoformat(),
            "status": p["status"],
            "card_last4": p["card_last4"],
            "cardholder": p["cardholder"],
            "account": entry.get("ACCOUNT", ""),
            "account_from": sources.get("ACCOUNT", ""),
            "class": entry.get("CLASS", ""),
            "department": entry.get("DEPARTMENT", ""),
            "blank_fields": " ".join(cod.get("blank", [])),
            "months_seen": " ".join(rec["evidence"]["months_seen"]),
            # Why it's a subscription: every piece of evidence, e.g. "on the vendor
            # list as a subscription; Brex category: Recurring software & SaaS;
            # charged in 2 earlier months (2026-07, 2026-08)".
            "reason": "; ".join(rec.get("why_subscription") or []) or rec["reason"],
            "transaction_id": tx["id"],
        })
    rows.sort(key=lambda r: (SHOWN.index(r["label"]), r["vendor"], r["transaction_date"]))
    return rows


def _quickbooks_rows(result):
    ready = [tx for tx in result["transactions"] if tx["inferred"]["coding"]["status"] == "ready"]
    ready.sort(key=lambda tx: (tx["parsed"]["transaction_date"], tx["id"]))
    return [tx["inferred"]["coding"]["entry"] for tx in ready]


def write(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result["run"]["inputs"]["month"]["file"]).stem
    qb_path = out_dir / f"{stem}.quickbooks.csv"
    review_path = out_dir / f"{stem}.recurring-review.csv"
    json_path = out_dir / f"{stem}.recurring.json"

    # Exactly the columns QuickBooks entry uses, in that order, and nothing else.
    with qb_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=QB_COLUMNS)
        w.writeheader()
        w.writerows(_quickbooks_rows(result))
    with review_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        w.writeheader()
        w.writerows(_review_rows(result))
    json_path.write_text(json.dumps(result, indent=2, default=to_json) + "\n", encoding="utf-8")
    return qb_path, review_path, json_path


def summary(result):
    run = result["run"]
    lines = []
    rows = _review_rows(result)
    width = max((len(r["vendor"]) for r in rows), default=6)
    for label in SHOWN:
        group = [r for r in rows if r["label"] == label]
        if not group:
            continue
        lines.append(f"\n{label} ({len(group)})")
        for r in group:
            shown = (f"account {r['account'] or '(blank)'}" if r["quickbooks"] == "ready"
                     else r["quickbooks"])
            lines.append(f"  {r['vendor']:<{width}}  {r['amount']:>9} {r['currency']}  "
                         f"{r['transaction_date']}  card {r['card_last4']}  {shown}")
            note = r["review"] or (r["reason"] if r["quickbooks"] != "ready" else "")
            if note:
                lines.append(f"  {'':<{width}}  {note}")

    if result["expected_but_missing"]:
        lines.append(f"\nexpected but missing ({len(result['expected_but_missing'])})")
        for m in result["expected_but_missing"]:
            last = f"last {m['last_amount']:.2f}" if m["last_amount"] is not None else "no history"
            lines.append(f"  {m['vendor']:<{width}}  seen {' '.join(m['months_seen']) or '-'}  {last}")

    c = run["counts"]
    files = run["inputs"]["history"]
    lines.append(f"\nhistory: {len(files)} file(s), covering "
                 f"{', '.join(c['history_months']) or 'no months'}")
    lines.append(f"{c['transactions']} transactions, {c['history_transactions']} in history, "
                 f"{c['unparsed_rows']} unparsed rows, {c['unmatched_descriptors']} unmatched descriptors")
    lines.append("quickbooks: " + ", ".join(f"{k} {v}" for k, v in c["coding"].items()))
    if c["blank_fields"]:
        lines.append("blank in QuickBooks entries: " +
                     ", ".join(f"{k} {v}" for k, v in c["blank_fields"].items()))
    if run["abstention_rate"] is not None:
        lines.append(f"flagged for review: {run['abstention_rate']:.1%} of QuickBooks entries")
    for w in run["warnings"]:
        lines.append(f"WARNING: {w}")
    return "\n".join(lines)
