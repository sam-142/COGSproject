# slack-safety

**Used by:** chase-list builder. Drafts are pasted into Slack by a person, so text from the export
must not be able to ping a channel or break the message's formatting.

| Row | Field | Text | Expected in the draft |
|---|---|---|---|
| `ss_here` | descriptor | `@here PROMO SHOP` | `(at)here PROMO SHOP` |
| `ss_channel` | descriptor | `<!channel> STORE` | `‹!channel› STORE` |
| `ss_backticks` | descriptor | ` ```TOOLS``` INC ` | `'''TOOLS''' INC` |
| `ss_holder` | cardholder | `@everyone` | `(at)everyone`, if a template uses `{cardholder}` |
