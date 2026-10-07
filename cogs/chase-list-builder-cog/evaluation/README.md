# evaluation

## fixtures/

All synthetic. Each folder is a copy of the folder with the same name in `sample-data/` at the repo
root, whose README says what the case tests and what should happen. `tests/test_cases.py` fails if a
copy drifts from `sample-data/`.

| Folder | What it tests |
|---|---|
| `baseline/` | a realistic month (September only); the demo runs on it |
| `three-day-exports/` | two exports three days apart; pending charges that post in between |
| `injection/` | text that reads like instructions. Blanking the memo and cardholder must change no decision, and no injected text may reach a draft |
| `malformed/` | bad rows, a missing column, an empty export, an Excel-style file |
| `routing/` | an unknown card and a missing card number: `needs-routing` |
| `receipts/` | every combination of receipt and memo, under both policy settings |
| `matching/` | two visits to the same place, a hold that never posts, the same merchant on another card |
| `slack-safety/` | descriptors and names that would ping a channel or break formatting |

When replies are read back in, they get their own injection fixture: they are the obvious place for
it.

## Results

None yet. The measure is whether the chase list matches what accounting would have chased in a real
month, and whether it was sent to the right place. Results go here as rates, never rows.
