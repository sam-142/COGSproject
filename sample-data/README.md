# sample-data

**Everything here is synthetic.** The cardholders, card numbers, transaction IDs and amounts are
made up. The vendors are real companies, used only so the descriptors look realistic. Real
statements and exports never go in this directory, or anywhere else in the repo: put them in
`private/`, which is gitignored.

## Test cases

One folder per case. Each has its CSVs and a README saying what it tests and what should happen.

| Folder | Used by | What it tests |
|---|---|---|
| [`context/`](context/) | both | the **invented** context files (vendors, coding rules, chart of accounts, known recurring, cards) the tests and demos run on. The Cogs' own defaults are empty |
| [`baseline/`](baseline/) | both | a realistic month (September 2026) and two months of history |
| [`three-day-exports/`](three-day-exports/) | chase-list | two exports three days apart; pending charges that post in between |
| [`injection/`](injection/) | both | text written as instructions, in the descriptor, memo and cardholder fields |
| [`malformed/`](malformed/) | both | bad rows, a missing column, only the required columns, an empty export, an Excel-style file |
| [`subscription-changes/`](subscription-changes/) | auto-coder | price rises inside and outside tolerance, a downgrade, usage drift, a card move |
| [`long-history/`](long-history/) | auto-coder | six months of history; one subscription cancelled months ago, one stopped last month |
| [`double-charge/`](double-charge/) | auto-coder | the same subscription charged twice on the same day |
| [`history-order/`](history-order/) | auto-coder | a later month passed in as history |
| [`usage-billing/`](usage-billing/) | auto-coder | a usage-billed jump, a fixed-price rise, a subscription not on the vendor list, a monthly contractor |
| [`routing/`](routing/) | chase-list | charges on an unknown card and with no card number |
| [`receipts/`](receipts/) | chase-list | every combination of receipt attached and memo filled in |
| [`declined/`](declined/) | both | a declined charge next to a normal one |
| [`matching/`](matching/) | chase-list | two visits to the same place, a hold that never posts, the same merchant on another card |
| [`slack-safety/`](slack-safety/) | chase-list | descriptors and names that would ping a channel or break formatting |

**Known gaps.** Three auto-coder cases describe behaviour that is wrong today: `long-history`
(a cancelled subscription is reported missing forever), `double-charge` (both charges are coded) and
`history-order` (the later month counts as evidence). Their tests are marked as expected failures,
and start failing loudly once the gap is fixed, so the mark gets removed.

## How the Cogs use these

Each Cog keeps copies of the folders it uses in its own `evaluation/fixtures/`, because a Cog can't
reference files outside its own folder. Each Cog's `tests/test_cases.py` checks that every copy
still matches the file here.

To change a case: edit it here, copy the folder into each Cog that uses it, and run `pixi run test`
in each.

To add a case: make a folder here with its CSVs and a README, copy it into the Cogs that use it,
add a section to their `tests/test_cases.py`, and add a row to the table above.

## Columns

Every CSV here uses **Brex's real export layout**: the same 70 columns, in the same order, as the
export accounting sent. All values are fake. `tools/profile_export.py` reports a match against the
real header.

The Cogs read only 22 of those columns; the reader (`cog_transactions/load.py`) drops the other 48
as each row is read. To prove that, the test files fill some dropped columns with recognisable fake
values (`…@fake-spender.example` emails, `receipts.fake-brex.example` links, "Fake Approver",
"Fake Attendee"), and each Cog has a test that fails if any of them appears in its output.

| Brex column | Read as | Required | Notes |
|---|---|---|---|
| `Id` | `transaction_id` | yes | unique per row |
| `Payment Status` | `status` | yes | `Cleared` → posted, `Declined` → declined, `Pending` → pending (assumed; not seen in a real export yet). Anything else: the row is unparsed |
| `Transaction Date` | `transaction_date` | yes | `MM/DD/YYYY` |
| `Posted Date` | `posted_date` | yes | blank unless posted |
| `Last 4` | `card_last4` | yes | becomes the QuickBooks REF NO. |
| `User` | `cardholder` | yes | the card's user; whether that's always the spender is an open question |
| `Merchant Name` | `merchant_name` | yes | Brex's cleaned-up name |
| `Statement Descriptor` | `merchant_descriptor` | yes | raw card-network text |
| `Amount`, `Currency` | `amount`, `currency` | yes | plain numbers (`45`, `1843.27`); `$` or `,` makes the row unparsed |
| `Original Amount`, `Original Currency` | `original_amount`, `original_currency` | no | filled on every row; only mentioned when the currency differs |
| `Type` | `type` | no | always `Card` so far |
| `Card Transaction Reference ID` | `reference_id` | no | candidate for QuickBooks REF NO. |
| `Brex Category` | `brex_category` | no | |
| `Memo` | `memo` | no | empty in the real export; the test files use it for injection cases |
| `Receipt URL` | `receipt_attached` | no | only *whether* it's filled; the link is never kept |
| `Department` | `spender_department` | no | the spender's team in Brex |
| `Integration Debit Line Category Fully Qualified Name` | `brex_account` | no | the expense account set in Brex, as QuickBooks names it; becomes the QuickBooks ACCOUNT |
| `Integration Class`, `Integration Department`, `Integration Vendor` | `brex_class`, `brex_department`, `brex_vendor` | no | empty or nearly empty in the real export |

**Refunds** are written here as negative amounts. The real export had none, so how Brex shows them is
still unknown.

**No link column.** Brex's export doesn't say which pending charge a posted one replaced, so every
pending-to-posted link is a match on card, merchant and date, flagged for checking.
