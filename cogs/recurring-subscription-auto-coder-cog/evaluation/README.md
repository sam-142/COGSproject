# evaluation

## fixtures/

All synthetic. Each folder is a copy of the folder with the same name in `sample-data/` at the repo
root, whose README says what the case tests and what should happen. `tests/test_cases.py` fails if a
copy drifts from `sample-data/`.

| Folder | What it tests |
|---|---|
| `baseline/` | a realistic September 2026, with July and August as history; the demo runs on it |
| `injection/` | text that reads like instructions, in the descriptor, memo and cardholder fields |
| `malformed/` | bad rows, a missing column, an empty export, an Excel-style file |
| `subscription-changes/` | price rises inside and outside ±10%, a downgrade, usage drift, a card move |
| `long-history/` | six months of history; a subscription cancelled months ago, one stopped last month |
| `double-charge/` | the same subscription charged twice on one day |
| `history-order/` | a later month passed in as history |

**Known gaps.** `long-history`, `double-charge` and `history-order` each contain a case the Cog gets
wrong today. Their tests are marked as expected failures (`xfail`, strict), so they show as `x` in
the test run. When a gap is fixed, its test passes, the run fails on the stale mark, and the mark gets
removed.

**What the injection fixture checks.** With no model step, an instruction in a descriptor can only
fail to match a vendor pattern, or match the vendor it names and be treated like any other charge
from that vendor. When a model step is added, this is the first fixture it must pass.

## Results

None yet. Accuracy is measured against accounting's real codings, which we don't have. When we
do, results go here as rates and anomalies, never rows.
