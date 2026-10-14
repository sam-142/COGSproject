# malformed

**Used by:** both Cogs. They share the reader (`cog_transactions/load.py`).

| File | Contents | Expected |
|---|---|---|
| `bad-rows.csv` | 2 good rows (one a refund), then: an empty amount, a day/month-swapped date (`13/01/2026`), Payment Status `Settled`, amount `twelve`, amount `$1,234.56`, an ISO date (`2026-09-07`) | the 2 good rows are read; the other 6 are listed as unparsed, each with its reason. The run carries on |
| `missing-column.csv` | no `Amount` column | the run stops with an error naming the missing column |
| `required-columns-only.csv` | only the 10 required columns, one good row | read normally; the run record lists the 12 optional columns as missing, and `receipt_attached` is unknown rather than false |
| `header-only.csv` | the header and no rows | runs cleanly and produces empty output |
| `excel-bom.csv` | one good row, saved the way Excel saves CSVs: a byte-order mark and Windows line endings | read normally |

**Note on `$1,234.56`.** It's rejected today. If the real Brex export writes amounts with a currency
sign or thousands separators, the reader must learn to accept them. This row is the reminder.
