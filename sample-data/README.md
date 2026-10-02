# sample-data

**Everything here is synthetic.** The cardholders, card numbers, transaction IDs and amounts are
made up. The vendors are real companies, used only so the descriptors look realistic. Real
statements and exports never go in this directory, or anywhere else in the repo.

## `brex-transactions-2026-09.csv`

A made-up month of OpenTeams Brex card activity, to build against until accounting sends a real
export (`cogs/questions.md`).

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

### Cases built into the file

The file is shaped to roughly match what accounting described: 51 transactions, about two thirds of
them recurring software charges, on 6 of the 10 cards. Two of those cards are shared heavily.

- **Recurring software** on the two shared engineering cards (4417, 8823). Some of these have
  receipts and some don't.
- **New subscription:** Grafana, with a memo saying so.
- **Same vendor, two descriptors:** AWS appears as both `AWS EMEA` and `Amazon Web Services`.
- **Same vendor twice in a month:** Slack's normal charge, then a mid-month charge (seats added).
- **Possible duplicate:** two Delta tickets for the same amount, one ticket number apart. These
  could be two travellers or a double charge.
- **Travel one-offs in GBP:** hotel, Uber, TfL and a team dinner, the kind of charge accounting
  finds hardest to chase.
- **Event marketing:** a booth and printing, also one-offs.
- **Refund:** an Eventbrite charge, then the same amount refunded.
- **Injection:** the Blue Bottle memo is written as an instruction. It must be treated as data, and
  nothing should act on it.
- **Pending to posted:**
  - `tx_0925a` is linked back to `px_0925a`. The pending row is no longer in the file because a
    posted row replaces it, as in a real export.
  - `tx_0926a` has no link, so the reader has to match it from card, merchant and date, and mark
    the match as inferred.
- **Still pending at the end of the month:** five charges, each with an amount that can still
  change:
  - a Marriott $1.00 card check, which will be replaced by the real charge;
  - a restaurant charge without the tip;
  - an `UBER *PENDING` charge whose descriptor will change when it posts.

  Chase these, but don't code them.

## `brex-transactions-2026-07.csv`, `brex-transactions-2026-08.csv`

History for the September file: September's recurring software charges, plus a few one-offs. The
differences from September are deliberate, so each recurrence label has a case:

| Case | Vendor | Expected label in September |
|---|---|---|
| in neither history month | Grafana | `new` |
| in August only | Canva | `likely-recurring` |
| September's second Slack charge (seats added) has no earlier match | Slack | `amount-changed` |
| charged in July and August, not September | Loom | expected but missing |
| usage-billed, drifting within ±10% | AWS, Datadog, Twilio | `recurring` |

### What it doesn't cover yet

- **Exports taken a few days apart.** The same charge is pending in one export and posted in the
  next. That's needed for testing the 3-day cadence.
