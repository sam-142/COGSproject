"""Describe the shape of a Brex CSV export without revealing its contents.

Run this yourself, in your own terminal, on a file in private/:

    python3 tools/profile_export.py private/<export>.csv

Don't run it through Claude or with Claude Code's `!` prefix: anything that
reaches the conversation goes to the cloud. Read the output first, then share
only what you're comfortable with.

What it prints:
  - row count, and how the header compares with the one we expect;
  - for every column, how often it is filled in;
  - for date, amount, ID and card-number columns, the *pattern* of the values,
    with digits and letters masked (2026-09-14 -> 9999-99-99, -1,234.56 -> -N,N.DD);
  - for a fixed list of status-type columns (Type, Expense Status, ...), their
    distinct values and counts. These are Brex's own labels, not your data;
  - whether the ID columns are unique, the sign of amounts, how many rows have
    no posted date, and how much of the accounting-integration coding is filled.

What it never prints: any row, name, email, merchant, memo, amount, ID, URL,
department, budget or policy name. Standard library only; no network.
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

EXPECTED = (
    "Swipe Time (UTC),Transaction Date,Posted Date,Payment Date,Exported Date,Exported Datetime,"
    "Amount,Currency,Original Amount,Original Currency,Purchased Amount,Purchased Currency,"
    "USD Equivalent Amount,Expense Status,Payment Status,Budget or Limit,Parent Budget,Policy,User,"
    "Department,Location,Cost Center,Statement Descriptor,Merchant Name,Brex Category,Memo,Type,"
    "Last 4,Employee Repayment Initiated By,Employee Repayment Initiation Date,Expense ID,Parent ID,"
    "Card Transaction Reference ID,Internal Attendees,External Attendees,Spender Email,"
    "Compliance Status,Current Review Assignees,Review Assigned Datetime,Final Approval Datetime,"
    "Final Approver,Final Copilot Approver,Integration Debit Line Category,"
    "Integration Debit Line Category Fully Qualified Name,Integration Credit Line Category,"
    "Integration Credit Line Category Fully Qualified Name,Integration Department,Integration Class,"
    "Integration Location,Integration Vendor,Integration Customer,Integration Project,"
    "Integration Employee,Integration Subsidiary,Integration Spending Entity,"
    "Integration Billing Entity,Integration External ID,Integration ERP Link,ERP Posting Date,"
    "Exported As,Previously Accrued,Previously Accrued Exported Date,Accrual reversal date,"
    "Additional travel data,Id,Receipt URL,Created From URL,Spending Entity in Brex,"
    "Billed Entity in Brex,Country of Expense"
).split(",")

DATES = ["Swipe Time (UTC)", "Transaction Date", "Posted Date", "Payment Date", "Exported Date",
         "Exported Datetime", "Employee Repayment Initiation Date", "Review Assigned Datetime",
         "Final Approval Datetime", "ERP Posting Date", "Previously Accrued Exported Date",
         "Accrual reversal date"]
AMOUNTS = ["Amount", "Original Amount", "Purchased Amount", "USD Equivalent Amount"]
IDS = ["Id", "Expense ID", "Parent ID", "Card Transaction Reference ID", "Last 4"]
# Brex's own labels. Safe to list; everything else is shown as fill rate only.
ENUMS = ["Type", "Expense Status", "Payment Status", "Compliance Status", "Currency",
         "Original Currency", "Purchased Currency", "Exported As", "Previously Accrued",
         "Brex Category"]
INTEGRATION = [c for c in EXPECTED if c.startswith("Integration ")]


def date_shape(v):
    return re.sub(r"\d", "9", v)


def amount_shape(v):
    # Integer digits -> N, decimal digits -> D: keeps sign, separators and decimals, hides size.
    v = re.sub(r"(?<=\.)\d+", lambda m: "D" * len(m.group()), v)
    return re.sub(r"\d+", "N", v)


def id_shape(v):
    s = re.sub(r"\d", "9", re.sub(r"[a-z]", "a", re.sub(r"[A-Z]", "A", v)))
    return re.sub(r"(9{5,}|a{5,}|A{5,})", lambda m: f"{m.group()[0]}{{{len(m.group())}}}", s)


def top(counter, n=5):
    return ", ".join(f"{k!r} x{c}" for k, c in counter.most_common(n)) or "-"


def main(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = list(reader)
    n = len(rows)
    print(f"file: {Path(path).name}")
    print(f"rows: {n}, columns: {len(header)}")

    missing = [c for c in EXPECTED if c not in header]
    extra = [c for c in header if c not in EXPECTED]
    print(f"header: {'matches expected' if not missing and not extra else 'DIFFERS'}")
    if missing:
        print(f"  missing: {missing}")
    if extra:
        print(f"  unexpected: {extra}")
    if header and header != [c for c in EXPECTED if c in header] + extra:
        print("  (columns are in a different order from expected)")
    if not n:
        return

    def filled(col):
        return [r[col].strip() for r in rows if (r.get(col) or "").strip()]

    print("\n== fill rate, every column")
    for col in header:
        print(f"  {len(filled(col)) / n:6.1%}  {col}")

    print("\n== value patterns (digits/letters masked)")
    for group, shape in ((DATES, date_shape), (AMOUNTS, amount_shape), (IDS, id_shape)):
        for col in group:
            if col in header:
                print(f"  {col}: {top(Counter(shape(v) for v in filled(col)))}")

    print("\n== distinct values of status-type columns")
    for col in ENUMS:
        if col in header:
            values = Counter(filled(col))
            print(f"  {col} ({len(values)} distinct): {top(values, 15)}")

    print("\n== checks")
    for col in ["Id", "Expense ID", "Card Transaction Reference ID"]:
        if col in header:
            vals = filled(col)
            dupes = len(vals) - len(set(vals))
            print(f"  {col}: {len(vals)} filled, {len(set(vals))} distinct "
                  f"({'no duplicates' if not dupes else f'{dupes} DUPLICATED'}"
                  f"{'' if len(vals) == n else f', blank on {n - len(vals)} rows'})")
    if "Id" in header and "Expense ID" in header:
        same = sum(r["Id"] == r["Expense ID"] for r in rows)
        print(f"  Id equals Expense ID on {same} of {n} rows")
    if "Swipe Time (UTC)" in header and "Transaction Date" in header:
        # Is Transaction Date month/day or day/month? Compare with the ISO swipe time.
        md = dm = 0
        for r in rows:
            iso, local = r["Swipe Time (UTC)"][:10], r["Transaction Date"].split("/")
            if len(local) == 3:
                md += iso == f"{local[2]}-{local[0]}-{local[1]}"
                dm += iso == f"{local[2]}-{local[1]}-{local[0]}"
        print(f"  Transaction Date agrees with Swipe Time read as MM/DD/YYYY on {md} rows, "
              f"as DD/MM/YYYY on {dm} rows (of {n}; time zones can shift a day)")
    if "Posted Date" in header:
        unposted = [r for r in rows if not r["Posted Date"].strip()]
        for col in ("Payment Status", "Expense Status"):
            if col in header and unposted:
                print(f"  rows with no Posted Date, by {col}: "
                      f"{dict(Counter(r[col] for r in unposted))}")
    if "Amount" in header:
        signs = Counter("negative" if v.lstrip().startswith(("-", "(")) else "positive"
                        for v in filled("Amount"))
        print(f"  Amount sign: {dict(signs)}")
    if "Posted Date" in header:
        print(f"  rows with no Posted Date (possibly pending): {n - len(filled('Posted Date'))}")
    if "Receipt URL" in header:
        print(f"  rows with a receipt: {len(filled('Receipt URL'))} of {n}")

    print("\n== accounting-integration coding (fill rate; distinct count, no values)")
    for col in INTEGRATION:
        if col in header:
            vals = filled(col)
            print(f"  {len(vals) / n:6.1%}  {len(set(vals)):4d} distinct  {col}")

    account = "Integration Debit Line Category"
    if account in header:
        print("\n== how consistent is the account coding? (counts only)")
        for key in ("Brex Category", "Merchant Name"):
            if key not in header:
                continue
            groups = {}
            for r in rows:
                if r[key].strip() and r[account].strip():
                    groups.setdefault(r[key].strip(), []).append(r[account].strip())
            seen_twice = {k: v for k, v in groups.items() if len(v) >= 2}
            one = sum(len(set(v)) == 1 for v in seen_twice.values())
            print(f"  {key}: {len(groups)} distinct; of the {len(seen_twice)} seen 2+ times, "
                  f"{one} always got the same account, {len(seen_twice) - one} got more than one")
        if "Brex Category" in header:
            per_account = {}
            for r in rows:
                if r[account].strip():
                    per_account.setdefault(r[account].strip(), set()).add(r["Brex Category"].strip())
            single = sum(len(c) == 1 for c in per_account.values())
            print(f"  accounts used: {len(per_account)}; {single} of them only ever holds one Brex Category")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 tools/profile_export.py private/<export>.csv")
    main(sys.argv[1])
