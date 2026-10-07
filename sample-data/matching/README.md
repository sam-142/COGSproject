# matching

**Used by:** chase-list builder. Two exports, three days apart.

| Charge | 13 Sep export (pending) | 16 Sep export (posted) | Expected |
|---|---|---|---|
| Oyster Bar visit 1, card 7742 | `mt_px_a`, 10 Sep, 50.00 | `mt_tx_a`, 10 Sep, 58.00, no link | matched to `mt_px_a` (same day), flagged for checking |
| Oyster Bar visit 2, card 7742 | `mt_px_b`, 11 Sep, 120.00 | `mt_tx_b`, 11 Sep, 138.00, no link | matched to `mt_px_b`, not to visit 1 |
| Oyster Bar, card 1290 | `mt_px_other_card`, 10 Sep, 50.00 | `mt_tx_other_card`, linked by the export | linked by the export; never matched across cards |
| Marriott hold, card 3308 | `mt_px_hold`, 1.00 | – (never posts) | stays pending and is chased |

With a chase log: run on the 13th's export and record the drafts as sent. A run on the 16th's export
then marks all three posted charges `already-chased` and drafts nothing.
