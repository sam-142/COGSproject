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
    """`coded` maps transaction id -> the auto-coder's coding status, or is empty."""
    for tx in transactions:
        p = tx["parsed"]
        entry, how = log.already_chased(tx, log_entries)

        if entry:
            if how.endswith("(matched by card, merchant and date)") and "pending_match" not in tx["inferred"]:
                record_match(tx, entry)
            status, reason = "already-chased", f"{how} was chased on {entry['sent_on']}"
        elif policy["skip_refunds"] and p["amount"] < 0:
            status, reason = "skip", "refund"
        elif policy["skip_coded_by_auto_coder"] and coded.get(tx["id"]) == "proposed":
            status, reason = "skip", "the auto-coder proposed a coding"
        elif policy["skip_when_receipt_and_memo"] and p["receipt_attached"] and p["memo"]:
            status, reason = "skip", "receipt attached and memo filled in"
        elif tx["inferred"]["route"]["channel"] is None:
            status, reason = "needs-routing", "card not in context/cards.yaml; a person picks who to ask"
        else:
            status = "draft"
            reason = ("the auto-coder couldn't code it" if coded.get(tx["id"]) == "needs-human"
                      else "no information on file for this charge")

        questions = [q for q in policy["ask_for"]
                     if not (q.get("skip_if") == "receipt_attached" and p["receipt_attached"])]
        infer(tx, "chase", {
            "source": "rule",
            "status": status,
            "reason": reason,
            "ask_for": [q["key"] for q in questions] if status in ("draft", "needs-routing") else [],
        })
