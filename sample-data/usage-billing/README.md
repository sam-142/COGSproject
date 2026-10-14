# usage-billing

**Used by:** auto-coder. Code `month-2026-09.csv` with both history files.

| Merchant | July → August → September | On the vendor list? | Expected in September |
|---|---|---|---|
| Datadog | 500.00 → 520.00 → 700.00 | yes, `billing: usage` | `recurring`, coded, flagged "amount up 34.6% on last charge" |
| Notion | 120.00 → 120.00 → 138.00 | yes, `billing: fixed` | `amount-changed`, needs a person |
| Retool | 310.00 → 295.40 → 455.10 | no; Brex category "Recurring software & SaaS" | `recurring` through Brex's Merchant Name, flagged; needs a person because there's no coding rule |
| Acme Consulting | 4000.00 every month | no; Brex category "Consultant & contractor" | `one-off`: monthly, but not a subscription category |

**September alone, with no history:** Datadog and Retool are `likely-recurring` (on the vendor list,
and on Brex's say-so); Acme Consulting is still `one-off`.
