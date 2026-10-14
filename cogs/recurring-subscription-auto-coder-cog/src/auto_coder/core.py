"""Run the steps in order. No interface code here, so any interface can call it."""
import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from auto_coder import coding, context, recurrence
from cog_transactions import SHAPE_VERSION, load, vendors

VERSION = "0.0.1"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(input_path, history_paths=(), context_dir=None):
    """`context_dir` is an override folder: its files replace this Cog's defaults."""
    ctx = context.load(context_dir)

    transactions, unparsed, columns = load.load_csv(input_path)
    columns = [columns]
    history = []
    for path in history_paths:
        txs, bad, cols = load.load_csv(path)
        history.extend(txs)
        unparsed.extend(bad)
        columns.append(cols)

    unmatched = vendors.identify(transactions, ctx["vendors"], ctx["subscription_categories"])
    vendors.identify(history, ctx["vendors"], ctx["subscription_categories"])
    missing = recurrence.label(transactions, history, ctx, history_supplied=bool(history_paths))
    coding.propose(transactions, ctx)

    labels = Counter(tx["inferred"]["recurrence"]["label"] for tx in transactions)
    vendor_sources = Counter(tx["inferred"]["vendor"]["source"] for tx in transactions)
    flagged = sum(1 for tx in transactions if tx["inferred"]["recurrence"]["amount_flag"])
    statuses = Counter(tx["inferred"]["coding"]["status"] for tx in transactions)
    # Of the entries made, how many carry a note for a person (a new vendor, one
    # month of history, an amount that moved)? The entry is made either way.
    entries = [tx["inferred"]["coding"] for tx in transactions
               if tx["inferred"]["coding"]["status"] == "ready"]
    in_scope = len(entries)
    abstained = sum(1 for c in entries if c["review"])
    blanks = Counter(k for c in entries for k in c["blank"])

    warnings = list(ctx["warnings"])
    if not history_paths:
        warnings.append("no history supplied: subscriptions are labelled likely-recurring at best, "
                        "and only the known-recurring list can establish a vendor")
    synthetic = [n for n, v in ctx["versions"].items() if v["status"] == "synthetic"]
    if synthetic:
        warnings.append(f"synthetic (invented) context files in use: {', '.join(synthetic)}")
    empty = [n for n, v in ctx["versions"].items() if v["status"] == "empty"]
    if empty:
        meaning = {"vendors": "merchants identified by Brex's name and category only",
                   "known-recurring": "only history can establish a vendor",
                   "coding-rules": "ACCOUNT comes from Brex; CLASS and DEPARTMENT stay blank unless Brex has them",
                   "chart-of-accounts": "rules aren't checked"}
        warnings.append("no real file supplied for: " +
                        "; ".join(f"{n} ({meaning[n]})" for n in empty))

    return {
        "run": {
            "cog": "recurring-subscription-auto-coder-cog",
            "version": VERSION,
            "transaction_shape": SHAPE_VERSION,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            # There is no model step yet. When there is, its binding goes here.
            "mode": "strict",
            "binding": None,
            "inputs": {
                "month": {"file": Path(input_path).name, "sha256": _sha256(input_path)},
                "history": [{"file": Path(p).name, "sha256": _sha256(p)} for p in history_paths],
            },
            # How much of each export was read: names and counts, never values.
            "columns": columns,
            "context": ctx["versions"],
            "tolerance": recurrence.TOLERANCE,
            "counts": {
                "transactions": len(transactions),
                "history_transactions": len(history),
                # Which months the history covers, so a missing file is visible.
                "history_months": sorted({f"{t['parsed']['transaction_date']:%Y-%m}" for t in history}),
                "unparsed_rows": len(unparsed),
                "unmatched_descriptors": len(unmatched),
                # Where each charge's vendor came from: the vendor list (context),
                # Brex's Merchant Name (export), or nowhere (none).
                "vendor_sources": dict(sorted(vendor_sources.items())),
                "amount_flags": flagged,
                "labels": dict(sorted(labels.items())),
                "coding": dict(sorted(statuses.items())),
                # How many QuickBooks entries have each field blank.
                "blank_fields": dict(sorted(blanks.items())),
            },
            # Share of QuickBooks entries flagged for a person to check.
            "abstention_rate": round(abstained / in_scope, 3) if in_scope else None,
            "warnings": warnings,
        },
        "transactions": transactions,
        "expected_but_missing": missing,
        "unmatched_descriptors": unmatched,
        "unparsed": unparsed,
    }
