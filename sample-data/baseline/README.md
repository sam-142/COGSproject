# baseline

A realistic month of OpenTeams Brex card activity, and the two months before it. The demo tasks of
both Cogs run on these.

## `brex-transactions-2026-09.csv`

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
