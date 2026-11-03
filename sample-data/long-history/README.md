# long-history

**Used by:** auto-coder. Code `month-2026-09.csv` with all six history files (March–August).

| Vendor | Charged | Expected in September |
|---|---|---|
| GitHub | every month, March–September | `recurring`, coded |
| Miro | every month March–August, not September | reported as expected but missing |
| Loom | March–May only; cancelled in June | **not** reported as missing: it stopped months ago |
| Figma | March, June, then September: gaps between charges | `likely-recurring`, flagged: charged in 2 earlier months, but not in each of the last 2 |

A vendor is established only when it charged in **each of the two months before** the month being
coded, so gaps (Figma) and stopped subscriptions (Loom) are both handled.
