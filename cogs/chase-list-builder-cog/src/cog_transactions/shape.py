"""Field names and the rules that make the shape the shape."""
from datetime import date

# Everything `parsed` may contain, in the order load.py fills it. Each is read
# from one Brex column (see load.COLUMNS); two are normalised on the way in:
# `status` from Payment Status, `receipt_attached` from whether Receipt URL is
# filled. Nothing here is inferred.
PARSED_FIELDS = (
    "transaction_id",
    "status",
    "transaction_date",
    "posted_date",
    "card_last4",
    "cardholder",
    "merchant_name",
    "merchant_descriptor",
    "amount",
    "currency",
    "original_amount",
    "original_currency",
    "type",
    "reference_id",
    "brex_category",
    "memo",
    "receipt_attached",
    "spender_department",
    "brex_account",
    "brex_class",
    "brex_department",
    "brex_vendor",
)
# A row without these can't be used at all; it is listed as unparsed.
REQUIRED_PARSED = ("transaction_id", "status", "transaction_date", "merchant_descriptor", "amount")
# `declined` rows are read, so they are counted, but neither Cog acts on them.
STATUSES = ("pending", "posted", "declined")

# Where an inferred value came from. Every inferred object names one.
INFERRED_SOURCES = (
    "context",   # a lookup file in the Cog's context/ directory
    "history",   # earlier months of transactions
    "rule",      # a rule from context/, applied to this transaction
    "match",     # matched against another transaction (pending -> posted)
    "export",    # derived directly from export values (e.g. Brex's Merchant Name and Category)
    "model",     # a model's answer; never treated as read from the statement
    "none",      # nothing could be worked out; the object says why
)


def new_transaction(parsed, source):
    return {"id": parsed["transaction_id"], "source": source, "parsed": parsed, "inferred": {}}


def infer(tx, key, value):
    """The one way to add an inferred value, so the shape's rules hold."""
    if key in PARSED_FIELDS:
        raise KeyError(f"{key!r} is a parsed field; it can't also be inferred")
    if value.get("source") not in INFERRED_SOURCES:
        raise ValueError(f"inferred {key!r} needs a source from {INFERRED_SOURCES}")
    tx["inferred"][key] = value


def to_json(o):
    """`default=` for json.dumps: dates become ISO strings."""
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(f"cannot serialise {type(o).__name__}")
