"""Field names and the rules that make the shape the shape."""
from datetime import date

# Everything `parsed` may contain. A loader for another export format (PDF,
# a real Brex CSV) must produce these names, and only these.
PARSED_FIELDS = (
    "transaction_id",
    "pending_transaction_id",
    "status",
    "transaction_date",
    "posted_date",
    "card_last4",
    "cardholder",
    "merchant_descriptor",
    "amount",
    "currency",
    "original_amount",
    "original_currency",
    "brex_category",
    "memo",
    "receipt_attached",
)
REQUIRED_PARSED = ("transaction_id", "status", "transaction_date", "merchant_descriptor", "amount")
STATUSES = ("pending", "posted")

# Where an inferred value came from. Every inferred object names one.
INFERRED_SOURCES = (
    "context",   # a lookup file in the Cog's context/ directory
    "history",   # earlier months of transactions
    "rule",      # a rule from context/, applied to this transaction
    "match",     # matched against another transaction (pending -> posted)
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
