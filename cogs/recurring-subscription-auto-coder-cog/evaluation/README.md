# evaluation

## fixtures/

All synthetic. See `sample-data/README.md` at the repo root for what each case in the monthly files
is for.

| File | Purpose |
|---|---|
| `brex-transactions-2026-09.csv` | the month to code |
| `brex-transactions-2026-07.csv`, `-08.csv` | history for it |
| `injection.csv` | text that reads like instructions, in the descriptor, the memo and the cardholder field |

The monthly files are copies of the ones in `sample-data/`, because a Cog can't reference files
outside its own folder. Keep the two copies identical.

**What the injection fixture checks.** Statement text is data, never direction. With no model step,
an instruction in a descriptor can only fail to match a vendor pattern, or match the vendor it names
and be treated like any other charge from that vendor. The fixture keeps that true. When a model
step is added, this is the first fixture it must pass.

## Results

None yet. Accuracy is measured against accounting's real codings, which we don't have. When we
do, results go here as rates and anomalies, never rows.
