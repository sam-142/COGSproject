"""Run the steps in order. No interface code here, so any interface can call it."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from cog_transactions import SHAPE_VERSION, combine, load, vendors
from chase_list import context, draft, log, select

VERSION = "0.0.1"
AUTO_CODER = "recurring-subscription-auto-coder-cog"


def _file(path):
    return {"file": Path(path).name, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def read_coded(path):
    """The auto-coder's JSON output -> {transaction id: (entry status, review note)}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (data.get("run") or {}).get("cog") != AUTO_CODER:
        raise ValueError(f"{Path(path).name} isn't output from {AUTO_CODER}")
    return {tx["id"]: (tx["inferred"]["coding"]["status"], tx["inferred"]["coding"].get("review"))
            for tx in data["transactions"]}


def run(inputs, coded_path=None, log_path=None, context_dir=None, template_path=None):
    """`context_dir` is an override folder: its files replace this Cog's defaults."""
    ctx = context.load(context_dir, template_path)

    batches, unparsed, columns = [], [], []
    for path in inputs:
        txs, bad, cols = load.load_csv(path)
        batches.append(txs)
        unparsed.extend(bad)
        columns.append(cols)
    rows_read = sum(len(b) for b in batches)

    transactions = combine.dedupe(batches)
    unmatched = vendors.identify(transactions, ctx["vendors"], ctx["subscription_categories"])
    transactions, superseded = combine.link(transactions)
    transactions.sort(key=lambda tx: (tx["parsed"]["transaction_date"], tx["id"]))

    coded = read_coded(coded_path) if coded_path else {}
    log_entries = log.read(log_path) if log_path else []

    select.route(transactions, ctx["cards"])
    select.decide(transactions, ctx["policy"], coded, log_entries)
    drafted = draft.drafts(transactions, ctx)

    statuses = Counter(tx["inferred"]["chase"]["status"] for tx in transactions)
    warnings = []
    synthetic = [n for n, v in ctx["versions"].items() if v["status"] in ("synthetic", "placeholder")]
    if synthetic:
        warnings.append(f"synthetic or placeholder context files in use: {', '.join(synthetic)}")
    empty = [n for n, v in ctx["versions"].items() if v["status"] == "empty"]
    if empty:
        meaning = {"vendors": "merchants identified by Brex's name and category only",
                   "cards": "every chase needs routing"}
        warnings.append("no real file supplied for: " +
                        "; ".join(f"{n} ({meaning.get(n, 'empty')})" for n in empty))
    if not log_path:
        warnings.append("no chase log: charges chased before will be drafted again")
    if not coded_path:
        warnings.append("no auto-coder output: recurring charges it would code are chased too")
    matched = [tx["id"] for tx in transactions if "pending_match" in tx["inferred"]]
    if matched:
        warnings.append(f"{len(matched)} posted charge(s) linked to a pending one by matching card, "
                        f"merchant and date, not by the export; check them: {', '.join(matched)}")

    dates = [tx["parsed"]["transaction_date"] for tx in transactions]
    return {
        "run": {
            "cog": "chase-list-builder-cog",
            "version": VERSION,
            "transaction_shape": SHAPE_VERSION,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            # There is no model step yet. When there is, its binding goes here.
            "mode": "strict",
            "binding": None,
            "inputs": [_file(p) for p in inputs],
            "coded": _file(coded_path) if coded_path else None,
            "log": {"file": Path(log_path).name, "entries": len(log_entries)} if log_path else None,
            # How much of each export was read: names and counts, never values.
            "columns": columns,
            "context": ctx["versions"],
            "template": ctx["template_file"],
            "period": {"from": min(dates), "to": max(dates)} if dates else None,
            "counts": {
                "rows_read": rows_read,
                "transactions": len(transactions),
                "duplicates_dropped": rows_read - len(transactions) - len(superseded),
                "pending_superseded": len(superseded),
                "unparsed_rows": len(unparsed),
                "unmatched_descriptors": len(unmatched),
                "chase": dict(sorted(statuses.items())),
                "drafts": len(drafted),
            },
            "warnings": warnings,
        },
        "transactions": transactions,
        "superseded": superseded,
        "drafts": drafted,
        "unmatched_descriptors": unmatched,
        "unparsed": unparsed,
    }
