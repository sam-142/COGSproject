"""Write results: the full JSON, a review CSV for accounting, and a terminal summary."""
import csv
import json
from pathlib import Path

from cog_transactions.shape import to_json

# The order labels appear in the review file and summary: what needs a person first.
SHOWN = ["amount-changed", "new", "likely-recurring", "recurring"]

REVIEW_COLUMNS = [
    "label", "coding_status", "vendor", "merchant_descriptor", "amount", "currency",
    "transaction_date", "status", "card_last4", "cardholder",
    "account", "class", "department", "entity",
    "months_seen", "reason", "transaction_id",
]


def _review_rows(result):
    rows = []
    for tx in result["transactions"]:
        rec, cod, p = tx["inferred"]["recurrence"], tx["inferred"]["coding"], tx["parsed"]
        if rec["label"] not in SHOWN:
            continue
        rows.append({
            "label": rec["label"],
            "coding_status": cod["status"],
            "vendor": tx["inferred"]["vendor"]["id"],
            "merchant_descriptor": p["merchant_descriptor"],
            "amount": f"{p['amount']:.2f}",
            "currency": p["currency"],
            "transaction_date": p["transaction_date"].isoformat(),
            "status": p["status"],
            "card_last4": p["card_last4"],
            "cardholder": p["cardholder"],
            "account": cod.get("account", ""),
            "class": cod.get("class", ""),
            "department": cod.get("department", ""),
            "entity": cod.get("entity", ""),
            "months_seen": " ".join(rec["evidence"]["months_seen"]),
            "reason": cod.get("reason") or rec["reason"],
            "transaction_id": tx["id"],
        })
    rows.sort(key=lambda r: (SHOWN.index(r["label"]), r["vendor"], r["transaction_date"]))
    return rows


def write(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result["run"]["inputs"]["month"]["file"]).stem
    json_path = out_dir / f"{stem}.recurring.json"
    csv_path = out_dir / f"{stem}.recurring-review.csv"

    json_path.write_text(json.dumps(result, indent=2, default=to_json) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        w.writeheader()
        w.writerows(_review_rows(result))
    return json_path, csv_path


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
            coded = (f"{r['account']} {r['class']}/{r['department']}"
                     if r["coding_status"] == "proposed" else r["coding_status"])
            lines.append(f"  {r['vendor']:<{width}}  {r['amount']:>9} {r['currency']}  "
                         f"{r['transaction_date']}  card {r['card_last4']}  {coded}")
            if r["coding_status"] != "proposed":
                lines.append(f"  {'':<{width}}  {r['reason']}")

    if result["expected_but_missing"]:
        lines.append(f"\nexpected but missing ({len(result['expected_but_missing'])})")
        for m in result["expected_but_missing"]:
            last = f"last {m['last_amount']:.2f}" if m["last_amount"] is not None else "no history"
            lines.append(f"  {m['vendor']:<{width}}  seen {' '.join(m['months_seen']) or '-'}  {last}")

    c = run["counts"]
    lines.append(f"\n{c['transactions']} transactions, {c['history_transactions']} in history, "
                 f"{c['unparsed_rows']} unparsed rows, {c['unmatched_descriptors']} unmatched descriptors")
    lines.append("coding: " + ", ".join(f"{k} {v}" for k, v in c["coding"].items()))
    if run["abstention_rate"] is not None:
        lines.append(f"abstention rate: {run['abstention_rate']:.1%} of posted recurring candidates")
    for w in run["warnings"]:
        lines.append(f"WARNING: {w}")
    return "\n".join(lines)
