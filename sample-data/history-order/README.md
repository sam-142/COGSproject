# history-order

**Used by:** auto-coder. Code `month-2026-08.csv`, passing `history-2026-07.csv` **and**
`later-2026-09.csv` as history.

Canva first appears in August, and again in September.

**Expected:** coding August, Canva is `new`: September hadn't happened yet. A later month should be
ignored as history, or the run should refuse it.

**Known gap:** today the September file counts as evidence, so Canva comes out `likely-recurring`.
The test is marked as an expected failure.
