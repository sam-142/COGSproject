"""Merge exports of any length into one set of transactions, and link pending
charges to the posted charges that replaced them.

Exports can overlap, and a charge that was pending in one export is posted in
the next, sometimes with a different amount and descriptor. Without this step
the same purchase would be counted, or chased, twice.

Two kinds of link:
    from the export   a posted row whose `pending_transaction_id` names the
                      pending row. Read, not inferred, so nothing is added.
    matched           no id link, so matched on card, merchant and date. Marked
                      as inferred (`inferred.pending_match`, source `match`),
                      because it is a judgement, not something the export said.

Run vendors.identify() first: matching compares vendor ids.
"""
import re

from cog_transactions.shape import infer

MATCH_WINDOW_DAYS = 3   # pending and posted transaction dates this close can match


def _rank(tx, order):
    # Same id in two exports: posted beats pending, then the later export wins.
    return (tx["parsed"]["status"] == "posted", order)


def dedupe(batches):
    """[[tx, ...], ...] in the order the files were given -> one list, one row per id."""
    best = {}
    for order, batch in enumerate(batches):
        for tx in batch:
            current = best.get(tx["id"])
            if current is None or _rank(tx, order) >= _rank(current[0], current[1]):
                best[tx["id"]] = (tx, order)
    return [tx for tx, _ in best.values()]


def _merchant_key(record):
    """Vendor id if known, else the start of the descriptor, letters and digits only.
    Descriptors get cut short differently when pending: `TST* LUCKY BAR & GRI`."""
    if record.get("vendor"):
        return record["vendor"]
    return re.sub(r"[^A-Z0-9]", "", (record.get("descriptor") or "").upper())[:10]


def summary(tx):
    """The few fields matching needs. Also what a chase log keeps, so a pending
    charge that has left the exports can still be matched later."""
    p = tx["parsed"]
    return {
        "transaction_id": tx["id"],
        "card_last4": p["card_last4"],
        "vendor": (tx["inferred"].get("vendor") or {}).get("id"),
        "descriptor": p["merchant_descriptor"],
        "transaction_date": p["transaction_date"],
        "amount": p["amount"],
    }


def match_pending(pending, posted_tx):
    """Best pending record for one posted transaction, or None.
    `pending` is a list of summary() dicts."""
    post = summary(posted_tx)
    best = None
    for pend in pending:
        if pend["card_last4"] != post["card_last4"] or _merchant_key(pend) != _merchant_key(post):
            continue
        days = abs((post["transaction_date"] - pend["transaction_date"]).days)
        if days > MATCH_WINDOW_DAYS:
            continue
        score = (days, abs(post["amount"] - pend["amount"]))
        if best is None or score < best[0]:
            best = (score, pend)
    return best[1] if best else None


def record_match(posted_tx, pend):
    infer(posted_tx, "pending_match", {
        "source": "match",
        "pending_transaction_id": pend["transaction_id"],
        "basis": "same card and merchant, transaction dates "
                 f"{abs((posted_tx['parsed']['transaction_date'] - pend['transaction_date']).days)} day(s) apart",
        "pending_amount": pend["amount"],
    })


def link(transactions):
    """Drop pending rows that a posted row in the same set replaces.
    Returns (remaining transactions, superseded: [{pending_id, replaced_by, how}])."""
    pending = {tx["id"]: tx for tx in transactions if tx["parsed"]["status"] == "pending"}
    superseded = []

    posted = [tx for tx in transactions if tx["parsed"]["status"] == "posted"]
    for tx in posted:
        pid = tx["parsed"]["pending_transaction_id"]
        if pid and pid in pending:
            superseded.append({"pending_id": pid, "replaced_by": tx["id"], "how": "export"})
            del pending[pid]

    for tx in posted:
        if tx["parsed"]["pending_transaction_id"]:
            continue
        pend = match_pending([summary(p) for p in pending.values()], tx)
        if pend:
            record_match(tx, pend)
            superseded.append({"pending_id": pend["transaction_id"], "replaced_by": tx["id"], "how": "match"})
            del pending[pend["transaction_id"]]

    gone = {s["pending_id"] for s in superseded}
    return [tx for tx in transactions if tx["id"] not in gone], superseded
