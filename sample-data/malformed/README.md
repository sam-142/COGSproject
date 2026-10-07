# malformed

**Used by:** both Cogs. They share the reader (`cog_transactions/load.py`).

| File | Contents | Expected |
|---|---|---|
| `bad-rows.csv` | 2 good rows (one a refund), then: an empty amount, month 13, status `settled`, amount `twelve`, amount `$1,234.56` | the 2 good rows are read; the other 5 are listed as unparsed, each with its reason. The run carries on |
| `missing-column.csv` | no `amount` column | the run stops with an error naming the missing column |
| `header-only.csv` | the header and no rows | runs cleanly and produces empty output |
| `excel-bom.csv` | one good row, saved the way Excel saves CSVs: a byte-order mark and Windows line endings | read normally |

**Note on `$1,234.56`.** It's rejected today. If the real Brex export writes amounts with a currency
sign or thousands separators, the reader must learn to accept them. This row is the reminder.
