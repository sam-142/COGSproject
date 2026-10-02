"""Label each charge recurring, likely-recurring, amount-changed, new or one-off.

No model. A charge is compared with the same vendor's charges in earlier months:

    established vendor = on the known-recurring list, or charged in 2+ earlier months
    recurring          = established, and the amount is within tolerance of an
                         earlier charge (or of the known amount)
    amount-changed     = established, but no earlier charge is within tolerance
    likely-recurring   = charged in exactly 1 earlier month, within tolerance
    new                = a subscription vendor never seen before
    one-off            = everything else, including every vendor whose category
                         in context/vendors.yaml isn't `subscription`

Amounts are matched charge by charge, not per vendor, so a vendor with two
separate subscriptions (two AWS accounts) is two streams rather than one
subscription that keeps changing price. Months are counted, not days: with a
monthly export, "charged in consecutive months" is what monthly means.
"""
from collections import defaultdict

from cog_transactions.shape import infer

TOLERANCE = 0.10  # ±10%, the default agreed for v0.0.1; see COG.md


def _month(tx):
    d = tx["parsed"]["transaction_date"]
    return f"{d.year:04d}-{d.month:02d}"


def _within(amount, reference):
    if reference == 0:
        return amount == 0
    return abs(amount - reference) / abs(reference) <= TOLERANCE


def label(transactions, history, ctx):
    """Fill tx["inferred"]["recurrence"] for each transaction.
    Returns the list of established vendors with no charge in `transactions`."""
    known = ctx["known_recurring"]

    # Only posted history counts. A pending row that later posted would
    # otherwise be counted twice, at two different amounts.
    by_vendor = defaultdict(list)
    current_ids = {tx["id"] for tx in transactions}
    for tx in history:
        vid = tx["inferred"]["vendor"]["id"]
        if vid and tx["parsed"]["status"] == "posted" and tx["id"] not in current_ids:
            by_vendor[vid].append(tx)

    for tx in transactions:
        vendor = tx["inferred"]["vendor"]
        vid = vendor["id"]
        amount = tx["parsed"]["amount"]
        prior = by_vendor.get(vid, [])
        prior_months = sorted({_month(p) for p in prior})
        matching = [p for p in prior if _within(amount, p["parsed"]["amount"])]
        matching_months = sorted({_month(p) for p in matching})

        known_entry = known.get(vid)
        known_amount_ok = (known_entry is not None
                           and (known_entry["amount"] is None
                                or _within(amount, float(known_entry["amount"]))))
        established = known_entry is not None or len(prior_months) >= 2
        source = "history"

        if vid is None:
            result, reason = "one-off", "vendor not recognised"
        elif vendor["category"] != "subscription":
            # Uber every month is still not a subscription.
            result, reason = "one-off", f"{vendor['category']} vendor"
        elif amount < 0:
            result, reason = "one-off", "refund"
        elif established and tx["parsed"]["status"] == "pending":
            # A pending amount is provisional, so comparing it with real ones
            # would flag every pre-authorisation as a price change.
            result, reason = "recurring", "established vendor; pending, so amount not compared yet"
        elif established:
            if len(matching_months) >= 2:
                result, reason = "recurring", "amount matches 2+ earlier months"
            elif known_amount_ok:
                result, reason, source = "recurring", "on the known-recurring list", "context"
            elif len(matching_months) == 1:
                result, reason = "likely-recurring", "established vendor; amount matches only 1 earlier month"
            else:
                result, reason = "amount-changed", "established vendor; no earlier charge within tolerance"
        elif len(matching_months) == 1:
            result, reason = "likely-recurring", "amount matches 1 earlier month"
        elif not prior:
            result, reason = "new", "subscription vendor not seen before"
        else:
            result, reason = "one-off", "seen before, but never at this amount"

        infer(tx, "recurrence", {
            "label": result,
            "reason": reason,
            "source": source,
            "evidence": {
                "known_recurring": known_entry is not None,
                "months_seen": prior_months,
                "months_matching_amount": matching_months,
                "earlier_amounts": sorted({p["parsed"]["amount"] for p in prior}),
            },
        })

    # Established vendors that didn't charge at all this period. Pending
    # charges count as charging: the money is on its way.
    charged = {tx["inferred"]["vendor"]["id"] for tx in transactions}
    subscriptions = {v["id"] for v in ctx["vendors"] if v["category"] == "subscription"}
    candidates = set(known) | {v for v, txs in by_vendor.items()
                               if v in subscriptions and len({_month(t) for t in txs}) >= 2}
    missing = []
    for vid in sorted(candidates - charged):
        prior = by_vendor.get(vid, [])
        missing.append({
            "vendor": vid,
            "known_recurring": vid in known,
            "months_seen": sorted({_month(p) for p in prior}),
            "last_amount": (max(prior, key=lambda p: p["parsed"]["transaction_date"])["parsed"]["amount"]
                            if prior else None),
        })
    return missing
