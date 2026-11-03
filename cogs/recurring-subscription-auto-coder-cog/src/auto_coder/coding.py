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
    MEMO        the memo already on the Brex charge, if any (never overwritten);
                else the subscription memo, built from quickbooks.yaml's
                `subscription_memo` template, the same way accounting's
                OT Vendor Subscription List builds it
    CLASS       a coding rule, else Brex's integration class
    DEPARTMENT  a coding rule, else Brex's integration department
    CHARGE      the amount

Separately, `review` says when a person should look at the label: a new
vendor, one month of history, or an amount that moved. That doesn't stop the
entry; it's a note in the review file.
"""
from cog_transactions.shape import infer

QB_COLUMNS = ["DATE", "REF NO.", "TYPE", "PAYEE", "ACCOUNT", "MEMO", "CLASS", "DEPARTMENT", "CHARGE"]

# Fields a subscription memo template may use -> the parsed field it reads.
MEMO_FIELDS = {
    "statement_descriptor": "merchant_descriptor",   # Brex column 23
    "merchant_name": "merchant_name",
    "department": "spender_department",              # Brex column 20, "Department"
    "card_last4": "card_last4",
    "cardholder": "cardholder",
    "brex_category": "brex_category",
}


def subscription_memo(parsed, template):
    """Fill the memo template from the charge. A blank field leaves no double
    space behind. Values are inserted as text, never interpreted."""
    text = template.format_map({k: parsed.get(f) or "" for k, f in MEMO_FIELDS.items()})
    return " ".join(text.split())
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
        "MEMO": _first((p["memo"], "export"),
                       (subscription_memo(p, qb["subscription_memo"]), "template")),
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
            notes = []
            if label in REVIEW_LABELS:
                notes.append(f"{label}: {rec['reason']}")
            elif rec.get("amount_flag"):
                notes.append(rec["amount_flag"])
            dup = rec["evidence"].get("duplicate")
            if dup:
                notes.append(f"possible duplicate of {dup['of']} (same vendor and amount on {dup['date']})")
            if sources["MEMO"] == "template" and "{department}" in qb["subscription_memo"] \
                    and not p["spender_department"]:
                notes.append("memo has no department: Brex's Department is blank")
            review = "; ".join(notes) or None
            coding = {
                "status": "ready",
                "source": "rule" if "rule" in sources.values() else "export",
                "entry": fields,
                "from": sources,
                "blank": [k for k in QB_COLUMNS if not fields[k]],
                "review": review,
            }
        infer(tx, "coding", coding)
