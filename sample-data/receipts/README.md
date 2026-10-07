# receipts

**Used by:** chase-list builder.

| Row | Receipt attached | Memo | Asks for (default policy) | With `skip_when_receipt_and_memo: true` |
|---|---|---|---|---|
| `rc_none` | no | no | purpose, department, receipt | drafted |
| `rc_receipt_only` | yes | no | purpose, department | drafted |
| `rc_receipt_and_memo` | yes | yes | purpose, department | **skipped** |
| `rc_memo_only` | no | yes | purpose, department, receipt | drafted |

Only whether the memo is filled in is checked, never what it says.
