"""Propose a QuickBooks coding for posted recurring charges.

Only charges labelled `recurring` are coded, and only once posted: a pending
amount and descriptor can still change. Everything else gets a status saying why
it wasn't coded, so nothing silently drops out.
"""
from cog_transactions.shape import infer


def propose(transactions, ctx):
    for tx in transactions:
        label = tx["inferred"]["recurrence"]["label"]
        vid = tx["inferred"]["vendor"]["id"]
        rule = ctx["rules"].get(vid)

        if label == "one-off":
            coding = {"status": "not-coded", "source": "none", "reason": "not a recurring charge"}
        elif tx["parsed"]["status"] == "pending":
            coding = {"status": "waiting-for-post", "source": "none",
                      "reason": "pending amounts can still change"}
        elif label != "recurring":
            reason = tx["inferred"]["recurrence"]["reason"]
            coding = {"status": "needs-human", "source": "none", "reason": f"{label}: {reason}"}
        elif rule is None:
            coding = {"status": "needs-human", "source": "none",
                      "reason": "no coding rule for this vendor"}
        else:
            coding = {"status": "proposed", "source": "rule", **rule}
        infer(tx, "coding", coding)
