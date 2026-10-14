"""Label each charge recurring, likely-recurring, amount-changed, new or one-off.

No model. A charge is compared with the same vendor's charges in earlier months.

    subscription       a vendor whose category is `subscription`, from the vendor
                       list or, for merchants not on it, from Brex's category
    established        on the known-recurring list, or charged in 2+ earlier months

    recurring          established, and either
                         - usage-billed: the amount is allowed to vary; a big
                           change is flagged, not blocked; or
                         - fixed-price: the amount is within tolerance of 2+
                           earlier charges, or of the known amount
    amount-changed     established, fixed-price, and no earlier charge is within
                       tolerance: a price rise, added seats, a downgrade
    likely-recurring   charged in exactly 1 earlier month (usage-billed, or at a
                       matching amount); or no history was supplied at all, so
                       the vendor list or Brex is the only evidence
    new                a subscription vendor not seen in the history supplied
    one-off            everything else: not a subscription, refunds, declined

A vendor's `billing` comes from the vendor list; when it isn't set (and for
every merchant not on the list) the vendor is treated as usage-billed. That
errs towards finding more subscriptions, with amount changes flagged for a
person, rather than missing them.

Fixed-price amounts are matched charge by charge, not per vendor, so a vendor
with two separate subscriptions (two AWS accounts) is two streams rather than one
that keeps changing price. Months are counted, not days: with a monthly export,
"charged in consecutive months" is what monthly means.
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


def _change(amount, prior):
    """Compare with the closest-in-amount charge in the vendor's latest earlier month."""
    if not prior:
        return None
    latest = max(_month(p) for p in prior)
    last = min((p["parsed"]["amount"] for p in prior if _month(p) == latest),
               key=lambda a: abs(a - amount))
    pct = None if last == 0 else round((amount - last) / abs(last) * 100, 1)
    return {"last_amount": last, "month": latest, "change_percent": pct}


def _describe(change):
    if not change or change["change_percent"] is None:
        return ""
    pct = change["change_percent"]
    if abs(pct) < 0.05:
        return "same as last charge"
    return f"{'up' if pct > 0 else 'down'} {abs(pct):g}% on last charge ({change['last_amount']:.2f})"


def _why_subscription(tx, prior_months, matching_months, known_entry, usage, categories):
    """Every piece of evidence that this charge is a subscription. Any combination
    can apply; the review CSV shows them all."""
    vendor, p = tx["inferred"]["vendor"], tx["parsed"]
    why = []
    if vendor["source"] == "context" and vendor["category"] == "subscription":
        billing = f", {vendor['billing']} billing" if vendor.get("billing") else ""
        why.append(f"on the vendor list as a subscription{billing}")
    if p.get("brex_category") in categories:
        why.append(f"Brex category: {p['brex_category']}")
    if known_entry is not None:
        why.append("on the known-recurring list")
    if prior_months:
        n = len(prior_months)
        why.append(f"charged in {n} earlier month{'s' if n != 1 else ''} ({', '.join(prior_months)})")
    if not usage and matching_months:
        n = len(matching_months)
        why.append(f"same amount (±10%) in {n} earlier month{'s' if n != 1 else ''}")
    return why


def label(transactions, history, ctx, history_supplied=True):
    """Fill tx["inferred"]["recurrence"] for each transaction.
    Returns the list of established vendors with no charge in `transactions`."""
    known = ctx["known_recurring"]
    categories = set(ctx.get("subscription_categories", ()))

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
        usage = vendor.get("billing") != "fixed"
        prior = by_vendor.get(vid, [])
        prior_months = sorted({_month(p) for p in prior})
        matching = [p for p in prior if _within(amount, p["parsed"]["amount"])]
        matching_months = sorted({_month(p) for p in matching})
        change = _change(amount, prior)
        changed = bool(change and change["change_percent"] is not None
                       and abs(change["change_percent"]) > TOLERANCE * 100)

        known_entry = known.get(vid)
        known_amount_ok = (known_entry is not None
                           and (known_entry["amount"] is None
                                or _within(amount, float(known_entry["amount"]))))
        established = known_entry is not None or len(prior_months) >= 2
        source = "history"
        flag = None

        if tx["parsed"]["status"] == "declined":
            result, reason = "one-off", "declined charge"
        elif vid is None:
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
        elif established and usage:
            result = "recurring"
            if known_entry is not None and not prior:
                reason, source = "on the known-recurring list", "context"
            else:
                reason = f"usage-billed; charged in {len(prior_months)} earlier months"
            if changed:
                flag = f"amount {_describe(change)}"
                reason += f"; {flag}"
        elif established:
            if len(matching_months) >= 2:
                result, reason = "recurring", "fixed price; amount matches 2+ earlier months"
            elif known_amount_ok:
                result, reason, source = "recurring", "on the known-recurring list", "context"
            elif len(matching_months) == 1:
                result, reason = "likely-recurring", "fixed price; amount matches only 1 earlier month"
            else:
                result, reason = "amount-changed", f"fixed price; amount {_describe(change) or 'differs from every earlier charge'}"
        elif prior and (usage or matching_months):
            result, reason = "likely-recurring", "charged in 1 earlier month"
        elif prior:
            result, reason = "one-off", "fixed price; seen before, but never at this amount"
        elif not history_supplied:
            result, source = "likely-recurring", vendor["source"]
            reason = ("no history supplied; " +
                      ("Brex categorises it as recurring software" if vendor["source"] == "export"
                       else "subscription on the vendor list"))
        else:
            result, reason = "new", "subscription vendor not seen before"

        infer(tx, "recurrence", {
            "label": result,
            "reason": reason,
            "source": source,
            "billing": "fixed" if not usage else "usage",
            "amount_flag": flag,
            # Why it counts as a subscription; empty for one-offs.
            "why_subscription": ([] if result == "one-off" else
                                 _why_subscription(tx, prior_months, matching_months,
                                                   known_entry, usage, categories)),
            "evidence": {
                "known_recurring": known_entry is not None,
                "months_seen": prior_months,
                "months_matching_amount": matching_months,
                "earlier_amounts": sorted({p["parsed"]["amount"] for p in prior}),
                "vs_last_charge": change,
            },
        })

    # Established vendors that didn't charge at all this period. Pending
    # charges count as charging: the money is on its way.
    charged = {tx["inferred"]["vendor"]["id"] for tx in transactions}
    # Subscriptions by the vendor list or, for merchants not on it, by Brex.
    candidates = set(known) | {v for v, txs in by_vendor.items()
                               if any(t["inferred"]["vendor"]["category"] == "subscription" for t in txs)
                               and len({_month(t) for t in txs}) >= 2}
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
