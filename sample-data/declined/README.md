# declined

**Used by:** both Cogs.

| Row | Payment Status | Expense Status | Expected |
|---|---|---|---|
| `dc_ok` | `Cleared` | `Approved` | treated normally |
| `dc_declined` | `Declined` | `Canceled` | read and counted, but never coded and never chased |

Mirrors the two declined rows in the real export, which had no posted date.
