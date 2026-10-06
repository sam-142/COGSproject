"""Write results: the full JSON, a chase-list CSV, the drafts for review, and a summary."""
import csv
import json
from pathlib import Path

from cog_transactions.shape import to_json

ORDER = ["needs-routing", "draft", "already-chased", "skip"]

LIST_COLUMNS = [
    "chase_status", "channel", "card_last4", "cardholder", "merchant_descriptor", "vendor",
    "amount", "currency", "transaction_date", "status", "asks_for", "reason", "draft_id",
    "transaction_id",
]


def _stem(result):
    period = result["run"]["period"]
    return f"chase_{period['from']}_to_{period['to']}" if period else "chase_empty"


def _rows(result):
    drafts = {d["transaction_id"]: d["id"] for d in result["drafts"]}
    rows = []
    for tx in result["transactions"]:
        p, inf = tx["parsed"], tx["inferred"]
        rows.append({
            "chase_status": inf["chase"]["status"],
            "channel": inf["route"]["channel"] or "",
            "card_last4": p["card_last4"] or "",
            "cardholder": p["cardholder"] or "",
            "merchant_descriptor": p["merchant_descriptor"],
            "vendor": inf["vendor"]["id"] or "",
            "amount": f"{p['amount']:.2f}",
            "currency": p["currency"] or "",
            "transaction_date": p["transaction_date"].isoformat(),
            "status": p["status"],
            "asks_for": " ".join(inf["chase"]["ask_for"]),
            "reason": inf["chase"]["reason"],
            "draft_id": drafts.get(tx["id"], ""),
            "transaction_id": tx["id"],
        })
    rows.sort(key=lambda r: (ORDER.index(r["chase_status"]), r["channel"], r["transaction_date"]))
    return rows


def _drafts_md(result):
    period = result["run"]["period"]
    lines = [f"# Chase drafts, {period['from']} to {period['to']}" if period else "# Chase drafts", "",
             "Nothing here has been sent. Review each draft, post the ones you want, then record",
             "them with `pixi run sent <the .chase.json file>` so they aren't drafted again.", ""]
    txs = {tx["id"]: tx for tx in result["transactions"]}
    groups = {}
    for d in result["drafts"]:
        groups.setdefault(d["channel"] or "NEEDS ROUTING: card not in context/cards.yaml", []).append(d)
    for channel in sorted(groups, key=lambda c: (not c.startswith("NEEDS"), c)):
        lines += [f"## {channel}", ""]
        for d in groups[channel]:
            p = txs[d["transaction_id"]]["parsed"]
            lines += [f"### {d['id']}: {p['merchant_descriptor']}, {p['amount']:.2f} {p['currency'] or ''}",
                      "", d["text"].rstrip(), "", "---", ""]
    return "\n".join(lines)


def write(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _stem(result)
    paths = (out_dir / f"{stem}.chase.json", out_dir / f"{stem}.chase-list.csv", out_dir / f"{stem}.drafts.md")
    paths[0].write_text(json.dumps(result, indent=2, default=to_json) + "\n", encoding="utf-8")
    with paths[1].open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LIST_COLUMNS)
        w.writeheader()
        w.writerows(_rows(result))
    paths[2].write_text(_drafts_md(result), encoding="utf-8")
    return paths


def summary(result):
    run, lines = result["run"], []
    rows = _rows(result)
    for status in ORDER[:3]:
        group = [r for r in rows if r["chase_status"] == status]
        if not group:
            continue
        lines.append(f"\n{status} ({len(group)})")
        for r in group:
            lines.append(f"  {r['channel'] or '-':<11} {r['merchant_descriptor'][:28]:<28} "
                         f"{r['amount']:>9} {r['currency']}  {r['transaction_date']}  {r['status']}")
            if status != "draft":
                lines.append(f"  {'':<11} {r['reason']}")
    skipped = [r for r in rows if r["chase_status"] == "skip"]
    if skipped:
        lines.append(f"\nskipped ({len(skipped)}): " + ", ".join(sorted({r['reason'] for r in skipped})))
    c = run["counts"]
    lines.append(f"\n{c['rows_read']} rows read, {c['transactions']} transactions, "
                 f"{c['duplicates_dropped']} duplicates dropped, {c['pending_superseded']} pending superseded, "
                 f"{c['unparsed_rows']} unparsed")
    lines.append(f"{c['drafts']} drafts. Nothing has been sent.")
    for w in run["warnings"]:
        lines.append(f"WARNING: {w}")
    return "\n".join(lines)
