"""Build the QuickBooks entry for each subscription charge.

Every posted charge labelled as a subscription gets an entry in QuickBooks'
format, with each field filled from the best source available and left blank
when nothing supplies it. A blank field never holds an entry back; only the
transaction itself can:

    ready             an entry was built; it goes in the QuickBooks file
    waiting-for-post  pending: the amount can still change, so no entry yet
    not-included      not a subscription (one-offs), a refund, or declined

Where each field comes from, in order of preference:

    DATE        the transaction date
    REF NO.     the field quickbooks.yaml names: the card's last 4 digits by
                default (Brex's Last 4); blank if the row has none
    TYPE        quickbooks.yaml's wording for a charge (or a credit)
    PAYEE       a coding rule's payee, else Brex's Integration Vendor, else
                Brex's Merchant Name
    ACCOUNT     a coding rule, else the account already on the Brex charge, by
                its fully qualified name
    MEMO        Brex's memo
    CLASS       a coding rule, else Brex's integration class
    DEPARTMENT  a coding rule, else Brex's integration department
    CHARGE      the amount

Separately, `review` says when a person should look at the label: a new
vendor, one month of history, or an amount that moved. That doesn't stop the
entry; it's a note in the review file.
"""
from cog_transactions.shape import infer

QB_COLUMNS = ["DATE", "REF NO.", "TYPE", "PAYEE", "ACCOUNT", "MEMO", "CLASS", "DEPARTMENT", "CHARGE"]
SUBSCRIPTION_LABELS = {"recurring", "likely-recurring", "new", "amount-changed"}
REVIEW_LABELS = {"likely-recurring", "new", "amount-changed"}


def _first(*candidates):
    """First (value, source) whose value is filled; else ("", "none")."""
    for value, source in candidates:
        if value not in (None, ""):
            return str(value), source
    return "", "none"


def _entry(tx, rule, qb):
    p = tx["parsed"]
    ref_value = tx["id"] if qb["ref_field"] == "transaction_id" else p.get(qb["ref_field"])
    ref, ref_from = _first((ref_value, "export"))
    if ref and qb["ref_max_length"]:
        ref = ref[-qb["ref_max_length"]:]     # the end of an ID is the distinctive part
    picks = {
        "DATE": (p["transaction_date"].strftime(qb["date_format"]), "export"),
        "REF NO.": (ref, ref_from),
        "TYPE": (qb["type_credit"] if p["amount"] < 0 else qb["type_charge"], "context"),
        "PAYEE": _first((rule.get("payee"), "rule"), (p["brex_vendor"], "export"),
                        (p["merchant_name"], "export"), (p["merchant_descriptor"], "export")),
        "ACCOUNT": _first((rule.get("account"), "rule"), (p["brex_account"], "export")),
        "MEMO": _first((p["memo"], "export")),
        "CLASS": _first((rule.get("class"), "rule"), (p["brex_class"], "export")),
        "DEPARTMENT": _first((rule.get("department"), "rule"), (p["brex_department"], "export")),
        "CHARGE": (f"{abs(p['amount']):.2f}", "export"),
    }
    fields = {k: v for k, (v, _) in picks.items()}
    sources = {k: s for k, (_, s) in picks.items()}
    return fields, sources


def propose(transactions, ctx):
    qb = ctx["quickbooks"]
    for tx in transactions:
        rec = tx["inferred"]["recurrence"]
        label = rec["label"]
        p = tx["parsed"]

        if p["status"] == "declined":
            coding = {"status": "not-included", "source": "none", "reason": "declined charge"}
        elif label not in SUBSCRIPTION_LABELS:
            coding = {"status": "not-included", "source": "none", "reason": f"not a subscription: {rec['reason']}"}
        elif p["status"] == "pending":
            coding = {"status": "waiting-for-post", "source": "none",
                      "reason": "pending: the amount can still change"}
        else:
            rule = ctx["rules"].get(tx["inferred"]["vendor"]["id"], {})
            fields, sources = _entry(tx, rule, qb)
            review = None
            if label in REVIEW_LABELS:
                review = f"{label}: {rec['reason']}"
            elif rec.get("amount_flag"):
                review = rec["amount_flag"]
            coding = {
                "status": "ready",
                "source": "rule" if "rule" in sources.values() else "export",
                "entry": fields,
                "from": sources,
                "blank": [k for k in QB_COLUMNS if not fields[k]],
                "review": review,
            }
        infer(tx, "coding", coding)
