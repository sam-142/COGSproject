# context

Files the code reads directly. Edit them; nothing needs rebuilding.

| File | What it controls |
|---|---|
| `cards.yaml` | each card's channel and users. Empty: real cards go in an override folder (`--context`) |
| `chase-policy.yaml` | which charges are chased, and what each message asks for |
| `message-template.md` | the wording of every drafted message |
| `vendors.yaml` | vendor list. Empty by default; **shared** with the auto-coder; keep the copies identical |
| `transaction.schema.json` | the transaction shape. **Shared** |
| `output-schema.json`, `output-example.json` | this Cog's output contract, and a short example of it |

## Editing the message template

`message-template.md` is plain text with placeholders in `{braces}`. Use any of these, in any
order, as often as you like:

| Placeholder | Becomes |
|---|---|
| `{card_last4}` | `4417` |
| `{cardholder}` | Brex `User` |
| `{channel}` | `#card-4417` |
| `{merchant}` | Brex's cleaned-up merchant name, e.g. `Delta Air Lines` |
| `{descriptor}` | the raw statement descriptor, e.g. `DELTA AIR 0062384719263` |
| `{vendor}` | the vendor id if recognised, else the descriptor |
| `{amount}`, `{currency}` | `684.40`, `USD` |
| `{original_amount}` | ` (originally 398.00 GBP)` when the original currency differs, otherwise empty |
| `{date}` | `2026-09-10` |
| `{status}` | `posted` or `pending` |
| `{status_note}` | for pending charges, a note that the amount may still change; otherwise empty |
| `{questions}` | the questions from `chase-policy.yaml`, one bullet each |
| `{reply_form}` | the fill-in form, starting with `ref: <transaction id>` |
| `{transaction_id}` | `tx_0910c` |

A placeholder that isn't in this list stops the run with an error naming it, so a typo can't
send a message with `{amonut}` in it. To print a literal brace, double it: `{{` or `}}`.

The memo is deliberately not available. It's free text that can say anything, and the person
who wrote it doesn't need it read back to them.

`--template PATH` uses a different template for one run.
