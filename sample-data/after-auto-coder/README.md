# after-auto-coder

**Used by:** chase-list builder. The auto-coder's updated statement for `baseline/`'s September
(`pixi run demo` in the auto-coder): the original export with the subscription memo
("… Paid by OT, Serving … OT") filled in on 31 subscription rows. This is the file the
chase-list builder is meant to run on.

| Rows | Expected |
|---|---|
| 31 subscriptions, now with a memo, plus 3 rows with a memo a cardholder typed | skipped: already has a memo |
| `px_0928a`, the pending AWS charge | skipped: a pending charge from a subscription vendor, which gets its memo once posted |
| the Eventbrite refund | skipped |
| the other 15 rows: flights, hotel, Ubers, events, printing, marketplace, including pending one-offs | **drafted** |

To regenerate after changing the auto-coder: run its `pixi run demo`, copy
`output/brex-transactions-2026-09.upload.csv` here, then into the chase-list builder's fixtures.
