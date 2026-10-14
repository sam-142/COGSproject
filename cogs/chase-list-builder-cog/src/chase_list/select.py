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


def decide(transactions, policy, coded, log_entries):
    """`coded` maps transaction id -> (the auto-coder's entry status, its review note),
    or is empty."""
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
        elif policy["skip_coded_by_auto_coder"] and entry_status == "ready" and not review:
            # A subscription the auto-coder put in the QuickBooks file with nothing
            # to check: accounting knows what it is, so there's nobody to ask.
            status, reason = "skip", "a subscription the auto-coder entered for QuickBooks"
        elif policy["skip_when_receipt_and_memo"] and p["receipt_attached"] and p["memo"]:
            status, reason = "skip", "receipt attached and memo filled in"
        elif tx["inferred"]["route"]["channel"] is None:
            status, reason = "needs-routing", "card not in context/cards.yaml; a person picks who to ask"
        else:
            status = "draft"
            reason = (f"the auto-coder flagged it: {review}" if review
                      else "no information on file for this charge")

        questions = [q for q in policy["ask_for"]
                     if not (q.get("skip_if") == "receipt_attached" and p["receipt_attached"])]
        infer(tx, "chase", {
            "source": "rule",
            "status": status,
            "reason": reason,
            "ask_for": [q["key"] for q in questions] if status in ("draft", "needs-routing") else [],
        })
