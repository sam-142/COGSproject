# double-charge

**Used by:** auto-coder. Code `month-2026-09.csv` with both history files.

Figma charged 135.00 in July and August, then **twice** on 2 September, for the same amount.

**Expected:** the first charge is coded; the second is flagged for a person as a possible double
charge.

Both are still entered (a flag never blocks an entry); the second carries the review note
"possible duplicate of dc_09_figma_a (same vendor and amount on 2026-09-02)".
