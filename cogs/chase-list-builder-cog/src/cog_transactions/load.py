"""CSV export -> transactions in the shared shape.

Only `parsed` is filled here. Nothing in this module infers anything.
"""
import csv
from datetime import date
from pathlib import Path

from cog_transactions.shape import PARSED_FIELDS, REQUIRED_PARSED, STATUSES, new_transaction

# Our field name -> the export's column header. This is a guess at Brex's
# export format; when a real export arrives, change the right-hand side here
# and nothing else.
COLUMNS = {
    "transaction_id": "transaction_id",
    "pending_transaction_id": "pending_transaction_id",
    "status": "status",
    "transaction_date": "transaction_date",
    "posted_date": "posted_date",
    "card_last4": "card_last4",
    "cardholder": "cardholder",
    "merchant_descriptor": "merchant_descriptor",
    "amount": "amount",
    "currency": "currency",
    "original_amount": "original_amount",
    "original_currency": "original_currency",
    "brex_category": "brex_category",
    "memo": "memo",
    "receipt_attached": "receipt_attached",
}
assert tuple(COLUMNS) == PARSED_FIELDS, "COLUMNS must map every parsed field, in order"


class ExportError(ValueError):
    """The file can't be read as an export at all (as opposed to one bad row)."""


def _parse_row(raw):
    out = {}
    for field, header in COLUMNS.items():
        value = (raw.get(header) or "").strip()
        out[field] = value or None

    missing = [f for f in REQUIRED_PARSED if not out[f]]
    if missing:
        raise ValueError(f"empty required field(s): {', '.join(missing)}")
    if out["status"] not in STATUSES:
        raise ValueError(f"unknown status {out['status']!r}")

    out["transaction_date"] = date.fromisoformat(out["transaction_date"])
    if out["posted_date"]:
        out["posted_date"] = date.fromisoformat(out["posted_date"])
    out["amount"] = round(float(out["amount"]), 2)
    if out["original_amount"]:
        out["original_amount"] = round(float(out["original_amount"]), 2)
    if out["receipt_attached"] is not None:
        out["receipt_attached"] = out["receipt_attached"].lower() == "true"
    return out


def load_csv(path):
    """Return (transactions, unparsed). A bad row goes to `unparsed` with a reason
    rather than stopping the run, so the run record can count it."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        absent = [COLUMNS[c] for c in REQUIRED_PARSED if COLUMNS[c] not in headers]
        if absent:
            raise ExportError(f"{path.name}: missing column(s) {', '.join(absent)}")

        transactions, unparsed = [], []
        for row_number, raw in enumerate(reader, start=2):  # row 1 is the header
            source = {"file": path.name, "row": row_number}
            try:
                parsed = _parse_row(raw)
            except ValueError as e:
                unparsed.append({**source, "reason": str(e)})
                continue
            transactions.append(new_transaction(parsed, source))
    return transactions, unparsed
