# double-charge

**Used by:** auto-coder. Code `month-2026-09.csv` with both history files.

Figma charged 135.00 in July and August, then **twice** on 2 September, for the same amount.

**Expected:** the first charge is coded; the second is flagged for a person as a possible double
charge.

**Known gap:** both are coded today, because each charge is compared with history on its own. The
test is marked as an expected failure.
