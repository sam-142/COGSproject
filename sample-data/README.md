# sample-data

**Everything here is synthetic.** The cardholders, card numbers, transaction IDs and amounts are
made up. The vendors are real companies, used only so the descriptors look realistic. Real
statements and exports never go in this directory, or anywhere else in the repo: put them in
`private/`, which is gitignored.

## Test cases

One folder per case. Each has its CSVs and a README saying what it tests and what should happen.

| Folder | Used by | What it tests |
|---|---|---|
| [`baseline/`](baseline/) | both | a realistic month (September 2026) and two months of history |
| [`three-day-exports/`](three-day-exports/) | chase-list | two exports three days apart; pending charges that post in between |
| [`injection/`](injection/) | both | text written as instructions, in the descriptor, memo and cardholder fields |
| [`malformed/`](malformed/) | both | bad rows, a missing column, an empty export, an Excel-style file |
| [`subscription-changes/`](subscription-changes/) | auto-coder | price rises inside and outside tolerance, a downgrade, usage drift, a card move |
| [`long-history/`](long-history/) | auto-coder | six months of history; one subscription cancelled months ago, one stopped last month |
| [`double-charge/`](double-charge/) | auto-coder | the same subscription charged twice on the same day |
| [`history-order/`](history-order/) | auto-coder | a later month passed in as history |
| [`routing/`](routing/) | chase-list | charges on an unknown card and with no card number |
| [`receipts/`](receipts/) | chase-list | every combination of receipt attached and memo filled in |
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

Every CSV here has the same columns.

**The columns are a guess.** We haven't seen a real Brex CSV yet. When one arrives, rename and
reorder these columns to match it, then fix the code that reads them. Don't assume these names.

| Column | Meaning |
|---|---|
| `transaction_id` | the export's ID for the row |
| `pending_transaction_id` | on a posted row, the ID of the pending charge it replaced. Blank when the export doesn't link them |
| `status` | `pending` or `posted` |
| `transaction_date` | when the card was used |
| `posted_date` | when it settled; blank while pending |
| `card_last4` | last four digits of the card. The PDF statement doesn't show these, but they are visible online |
| `cardholder` | name the card is under, which isn't necessarily who used it |
| `merchant_descriptor` | raw text from the card network |
| `amount`, `currency` | in USD; positive is a charge, negative is a refund |
| `original_amount`, `original_currency` | the amount in the original currency, for foreign charges |
| `brex_category` | Brex's guess from the vendor. Accounting doesn't use it |
| `memo` | free text entered by the cardholder |
| `receipt_attached` | `true` / `false` |
