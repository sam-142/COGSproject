"""Brex CSV export -> transactions in the shared shape.

This is also where the export is trimmed. A Brex export has 70 columns; only the
ones in COLUMNS are read. The rest (spender emails, receipt links, approvers,
budgets, attendees...) are dropped as each row is read and never reach a
transaction, an output file or a draft.

Only `parsed` is filled here. Nothing in this module infers anything.
"""
import csv
from datetime import datetime
from pathlib import Path

from cog_transactions.shape import PARSED_FIELDS, REQUIRED_PARSED, STATUSES, new_transaction

# Our field name -> (Brex column, required?). A required column missing from the
# header stops the run; a missing optional one just leaves the field empty.
# If Brex renames a column, change it here and nowhere else.
COLUMNS = {
    "transaction_id": ("Id", True),
    "status": ("Payment Status", True),
    "transaction_date": ("Transaction Date", True),
    "posted_date": ("Posted Date", True),
    "card_last4": ("Last 4", True),
    "cardholder": ("User", True),
    "merchant_name": ("Merchant Name", True),
    "merchant_descriptor": ("Statement Descriptor", True),
    "amount": ("Amount", True),
    "currency": ("Currency", True),
    "original_amount": ("Original Amount", False),
    "original_currency": ("Original Currency", False),
    "type": ("Type", False),
    "reference_id": ("Card Transaction Reference ID", False),
    "brex_category": ("Brex Category", False),
    "memo": ("Memo", False),
    "receipt_attached": ("Receipt URL", False),
    "spender_department": ("Department", False),
    # The fully qualified name (e.g. "Expenses:Software Subscriptions") is what
    # accounting enters as the QuickBooks ACCOUNT.
    "brex_account": ("Integration Debit Line Category Fully Qualified Name", False),
    "brex_class": ("Integration Class", False),
    "brex_department": ("Integration Department", False),
    "brex_vendor": ("Integration Vendor", False),
}
assert tuple(COLUMNS) == PARSED_FIELDS, "COLUMNS must map every parsed field, in order"

# Payment Status -> our status. "Pending" is an assumption: the one real export
# seen so far had no pending charges. Any other value makes the row unparsed,
# with the value named, so a new status shows up instead of being guessed at.
PAYMENT_STATUS = {"cleared": "posted", "pending": "pending", "declined": "declined"}
assert set(PAYMENT_STATUS.values()) <= set(STATUSES)

DATE_FORMAT = "%m/%d/%Y"   # Brex writes 09/14/2026


class ExportError(ValueError):
    """The file can't be read as an export at all (as opposed to one bad row)."""


def _date(value):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"date {value!r} isn't MM/DD/YYYY") from None


def _amount(value):
    # Plain numbers only ("45", "45.5", "1843.27"). "$1,234.56" is rejected, so a
    # change in Brex's number format shows up as unparsed rows, not wrong amounts.
    try:
        return round(float(value), 2)
    except ValueError:
        raise ValueError(f"amount {value!r} isn't a plain number") from None


def _parse_row(raw, present):
    out = {}
    for field, (column, _) in COLUMNS.items():
        value = (raw.get(column) or "").strip() if column in present else ""
        out[field] = value or None

    missing = [f for f in REQUIRED_PARSED if not out[f]]
    if missing:
        raise ValueError(f"empty required field(s): {', '.join(missing)}")

    status = PAYMENT_STATUS.get(out["status"].lower())
    if status is None:
        raise ValueError(f"unknown Payment Status {out['status']!r}")
    out["status"] = status

    out["transaction_date"] = _date(out["transaction_date"])
    if out["posted_date"]:
        out["posted_date"] = _date(out["posted_date"])
    out["amount"] = _amount(out["amount"])
    if out["original_amount"]:
        out["original_amount"] = _amount(out["original_amount"])
    # Whether a receipt link exists, never the link itself.
    out["receipt_attached"] = (out["receipt_attached"] is not None
                               if "Receipt URL" in present else None)
    return out


def load_csv(path):
    """Return (transactions, unparsed, columns).

    A bad row goes to `unparsed` with a reason rather than stopping the run, so
    the run record can count it. `columns` says how much of the export was read:
    column names and counts only, never values."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [h.strip() for h in (reader.fieldnames or [])]
        reader.fieldnames = header
        present = set(header)
        absent = [col for col, required in COLUMNS.values() if required and col not in present]
        if absent:
            raise ExportError(f"{path.name}: missing column(s) {', '.join(absent)}")

        transactions, unparsed = [], []
        for row_number, raw in enumerate(reader, start=2):  # row 1 is the header
            source = {"file": path.name, "row": row_number}
            try:
                parsed = _parse_row(raw, present)
            except ValueError as e:
                unparsed.append({**source, "reason": str(e)})
                continue
            transactions.append(new_transaction(parsed, source))

    used = {col for col, _ in COLUMNS.values()}
    columns = {
        "file": path.name,
        "read": len(used & present),
        "ignored": len(present - used),
        "optional_missing": sorted(col for col, required in COLUMNS.values()
                                   if not required and col not in present),
    }
    return transactions, unparsed, columns
