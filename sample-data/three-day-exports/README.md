# three-day-exports

**Used by:** chase-list builder.

Two exports taken three days apart, as if Brex were exported every few days. Built from the
September file.

| Charge | 27 Sep export | 30 Sep export |
|---|---|---|
| Uber, card 3308 | pending `px_0925a`, `UBER *PENDING`, 23.50 | posted `tx_0925a`, 27.80, **linked** to `px_0925a` by the export |
| Lucky Bar, card 7742 | pending `px_0926z`, `TST* LUCKY BAR & GRI`, 80.00 | posted `tx_0926a`, 96.25 with tip, **not linked**: only matchable by card, merchant and date |
| Lucky Bar again, card 7742 | – | pending `px_0930b`, 4 days later: a different visit, must not be matched |

## Expected

- Run on the 27th's export, then record the drafts as sent: next run, on the 30th's export, the Uber
  and first Lucky Bar charges are `already-chased`. The Uber link comes from the export; the Lucky
  Bar link is matched and flagged for checking.
- Run on both exports together: the two pending rows are dropped as superseded, and only the posted
  versions are chased.
- The second Lucky Bar visit (`px_0930b`) is always chased as a new charge.
