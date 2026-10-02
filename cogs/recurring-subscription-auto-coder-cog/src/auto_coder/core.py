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


def run(input_path, history_paths=(), context_dir=context.DEFAULT_DIR):
    ctx = context.load(context_dir)

    transactions, unparsed = load.load_csv(input_path)
    history = []
    for path in history_paths:
        txs, bad = load.load_csv(path)
        history.extend(txs)
        unparsed.extend(bad)

    unmatched = vendors.identify(transactions, ctx["vendors"])
    vendors.identify(history, ctx["vendors"])
    missing = recurrence.label(transactions, history, ctx)
    coding.propose(transactions, ctx)

    labels = Counter(tx["inferred"]["recurrence"]["label"] for tx in transactions)
    statuses = Counter(tx["inferred"]["coding"]["status"] for tx in transactions)
    # Of the charges this Cog is meant to code (posted, not one-off), how many
    # did it decline? Low is only good if the codings it did make are right.
    in_scope = sum(1 for tx in transactions
                   if tx["inferred"]["recurrence"]["label"] != "one-off"
                   and tx["parsed"]["status"] == "posted")
    abstained = statuses.get("needs-human", 0)

    warnings = []
    if not history_paths:
        warnings.append("no history supplied: only the known-recurring list can establish a vendor")
    synthetic = [n for n, v in ctx["versions"].items() if v["status"] == "synthetic"]
    if synthetic:
        warnings.append(f"synthetic context files in use: {', '.join(synthetic)}")

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
            "context": ctx["versions"],
            "tolerance": recurrence.TOLERANCE,
            "counts": {
                "transactions": len(transactions),
                "history_transactions": len(history),
                "unparsed_rows": len(unparsed),
                "unmatched_descriptors": len(unmatched),
                "labels": dict(sorted(labels.items())),
                "coding": dict(sorted(statuses.items())),
            },
            "abstention_rate": round(abstained / in_scope, 3) if in_scope else None,
            "warnings": warnings,
        },
        "transactions": transactions,
        "expected_but_missing": missing,
        "unmatched_descriptors": unmatched,
        "unparsed": unparsed,
    }
