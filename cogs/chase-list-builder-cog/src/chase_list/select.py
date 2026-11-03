"""Decide, for each charge, whether to chase it, and where the message goes.

Adds two inferred keys to every transaction:
    route   the card's channel, from context/cards.yaml
    chase   the decision: draft, already-chased or skip, with the reason

Chase on pending: a pending charge is chased straight away, because people
remember what they bought on Tuesday, not three weeks later.
"""
from cog_transactions.combine import record_match
from cog_transactions.shape import infer

from chase_list import log


def route(transactions, cards):
    for tx in transactions:
        card = cards.get(tx["parsed"]["card_last4"])
        if card and card["channel"]:
            infer(tx, "route", {"source": "context", "channel": card["channel"],
                                "users": card["users"], "shared": card["shared"]})
        else:
            infer(tx, "route", {"source": "none", "channel": None,
                                "reason": "card not in context/cards.yaml"})


def subscription_vendors(transactions, marker):
    """Vendors with at least one row carrying the auto-coder's subscription memo
    (it contains `marker`, e.g. "Paid by OT, Serving")."""
    if not marker:
        return set()
    return {tx["inferred"]["vendor"]["id"] for tx in transactions
            if tx["inferred"]["vendor"]["id"] and marker in (tx["parsed"]["memo"] or "")}


def decide(transactions, policy, coded, log_entries):
    """`coded` maps transaction id -> (the auto-coder's entry status, its review note),
    or is empty.

    Built to run on the auto-coder's updated statement: every subscription there
    already has its memo, so what's left without one is what to chase."""
    subs = subscription_vendors(transactions, policy["subscription_memo_marker"])
    for tx in transactions:
        p = tx["parsed"]
        entry_status, review = coded.get(tx["id"], (None, None))
        entry, how = log.already_chased(tx, log_entries)

        if entry:
            if how.endswith("(matched by card, merchant and date)") and "pending_match" not in tx["inferred"]:
                record_match(tx, entry)
            status, reason = "already-chased", f"{how} was chased on {entry['sent_on']}"
        elif p["status"] == "declined":
            status, reason = "skip", "declined charge"
        elif policy["skip_refunds"] and p["amount"] < 0:
            status, reason = "skip", "refund"
        elif policy["skip_coded_by_auto_coder"] and entry_status in ("ready", "waiting-for-post"):
            # A subscription, as far as the auto-coder is concerned. If it flagged
            # it for review, that review is accounting's, not a cardholder's.
            status, reason = "skip", ("a subscription the auto-coder flagged for accounting's review"
                                      if review else "a subscription the auto-coder handles")
        elif policy["skip_when_memo"] and p["memo"]:
            status, reason = "skip", "already has a memo"
        elif p["status"] == "pending" and tx["inferred"]["vendor"]["id"] in subs:
            # A pending charge from a vendor whose other rows carry the subscription
            # memo: the auto-coder gives it a memo once it posts.
            status, reason = "skip", "pending charge from a subscription vendor; it gets its memo once posted"
        elif policy["skip_when_receipt_and_memo"] and p["receipt_attached"] and p["memo"]:
            status, reason = "skip", "receipt attached and memo filled in"
        elif tx["inferred"]["route"]["channel"] is None:
            status, reason = "needs-routing", "card not in context/cards.yaml; a person picks who to ask"
        else:
            status, reason = "draft", "no memo: nothing on file says what this charge was for"

        questions = [q for q in policy["ask_for"]
                     if not (q.get("skip_if") == "receipt_attached" and p["receipt_attached"])]
        infer(tx, "chase", {
            "source": "rule",
            "status": status,
            "reason": reason,
            "ask_for": [q["key"] for q in questions] if status in ("draft", "needs-routing") else [],
        })
