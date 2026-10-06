"""The chase log: which charges have actually been chased.

A charge is recorded only when a person says the message was sent
(`pixi run sent`), never when it is drafted. A draft that was thrown away must
come back next run; a message that was sent must not.

The log holds transaction details (card, merchant, date, amount), so keep it
out of the repo: the default file name is gitignored, or put it in private/.
"""
import json
from datetime import date
from pathlib import Path

from cog_transactions.combine import match_pending
from cog_transactions.shape import to_json

FORMAT = 1


def read(path):
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise ValueError(f"{path}: not a chase log this version understands")
    entries = data.get("chased", [])
    for e in entries:
        e["transaction_date"] = date.fromisoformat(e["transaction_date"])
    return entries


def write(path, entries):
    Path(path).write_text(json.dumps({"format": FORMAT, "chased": entries}, indent=2,
                                     default=to_json) + "\n", encoding="utf-8")


def already_chased(tx, entries):
    """Return (log entry, how) if this charge, or the pending charge it replaced,
    has been chased before. Otherwise (None, None)."""
    by_id = {e["transaction_id"]: e for e in entries}
    if tx["id"] in by_id:
        return by_id[tx["id"]], "same transaction"
    pid = tx["parsed"]["pending_transaction_id"]
    if pid and pid in by_id:
        return by_id[pid], "its pending charge (linked in the export)"
    matched = (tx["inferred"].get("pending_match") or {}).get("pending_transaction_id")
    if matched and matched in by_id:
        return by_id[matched], "its pending charge (matched by card, merchant and date)"
    if tx["parsed"]["status"] == "posted" and not pid:
        pend = match_pending([e for e in entries if e.get("status") == "pending"], tx)
        if pend:
            return pend, "its pending charge (matched by card, merchant and date)"
    return None, None
