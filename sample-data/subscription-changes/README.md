# subscription-changes

**Used by:** auto-coder. Code `month-2026-09.csv` with both history files.

| Row | July → August → September | Expected in September |
|---|---|---|
| `sc_09_figma` | 135.00 → 135.00 → 145.80 (+8%) | `recurring`, coded |
| `sc_09_notion` | 120.00 → 120.00 → 138.00 (+15%) | `amount-changed`, needs a person |
| `sc_09_zoom` | 149.90 → 149.90 → 74.95 (−50%, a downgrade) | `amount-changed`, needs a person |
| `sc_09_hubspot` | 890.00 every month | `recurring`, coded |
| `sc_09_datadog` | 575.00 → 640.00 → 600.00 (usage-billed, drifting both ways) | `recurring`, coded |
| `sc_09_linear` | 128.00 every month, but moved from card 8823 to card 4417 in September | `recurring`, coded: recurrence is by vendor, not card |
