# COG implementation

**This is where the implementations for the cogs Chase-List Builder and Recurring subscription auto-coder live**,

---

each folder currently contains a COG.md file, a cog.yaml file, a skills folder, a frames folder, and a references folder. These COGS are to be build by referencing (but not bound by) the cogspec (SPEC.md) written by Trent Oliphant.

---

**Hurdles**

Here are some things I think it is worth keeping in mind during development:

**Pending transactions**

Card transactions appear pending with a provisional amount and a descriptor that often changes on settlement two to four days later. At a 3-day cadence we will see both states constantly. Proposed solution: chase on pending, code on posted. Chasing early is better because people remember what they bought on Tuesday, not three weeks ago, but never propose a QuickBooks coding off an amount that can still change. Most aggregators give you a link from the posted transaction back to its pending ID; if yours doesn't, match on card, merchant and date proximity and mark the link as inferred.

---

**Current Architecture:**


Two independent Cogs, each its own pixi package. There is no shared parsing Cog: the part both need
(reading transactions into one shape) lives in the auto-coder and gets **copied** into the
chase-list builder unchanged.

| Cog | Status |
|---|---|
| `recurring-subscription-auto-coder-cog` | a Cog (has its manifest): runs end to end on the synthetic CSVs, no model step yet |
| `chase-list-builder-cog` | empty |

---

**Recurring subscription auto-coder**

```
recurring-subscription-auto-coder-cog/
  COG.md              what the Cog does and doesn't do
  cog.yaml            manifest: requirements, interfaces, where context lives
  pixi.toml           environment + tasks (the Cog's commands)
  pyproject.toml      makes src/ installable

  src/cog_transactions/   SHARED - copied unchanged into chase-list-builder-cog
    shape.py              the transaction shape and its rules
    load.py               CSV -> transactions
    vendors.py            merchant descriptor -> vendor

  src/auto_coder/         this Cog only
    cli.py                commands: code, check, use
    core.py               runs the steps in order, builds the run record
    context.py            loads and cross-checks the YAML in context/
    recurrence.py         labels each charge
    coding.py             proposes QuickBooks codings
    report.py             writes JSON, review CSV, terminal summary
    model.py              model settings + one-token test (not used by the pipeline yet)

  context/            data the code reads
    vendors.yaml              SHARED - descriptor patterns -> vendor
    known-recurring.yaml      vendors accounting knows recur
    coding-rules.yaml         vendor -> account / class / department / entity
    chart-of-accounts.yaml    what a rule is allowed to use
    transaction.schema.json   SHARED - the transaction shape
    output-schema.json        the full output contract
    output-example.json       a short real output

  frames/             Markdown org context for the model (nothing reads it yet)
    recurring-subscriptions.md
    coding-conventions.md

  evaluation/fixtures/   synthetic July-September 2026 CSVs + injection.csv
  tests/                 24 tests
```

All four YAML files in `context/` are synthetic placeholders until accounting sends the real ones.
Every run warns about this.

**How a run flows:**

```
CSV for the month + CSVs for earlier months
  -> load        parsed: exactly what the CSV says
  -> vendors     inferred.vendor       (from context/vendors.yaml)
  -> recurrence  inferred.recurrence   (compared against earlier months)
  -> coding      inferred.coding       (from context/coding-rules.yaml)
  -> report      output/<name>.recurring.json
                 output/<name>.recurring-review.csv
```

Every transaction has a `parsed` object (read from the CSV) and an `inferred` object (worked out
afterwards, each value naming its source). A field can't be in both: the schema rejects it and the
code refuses to write it.

Recurrence labels: `recurring`, `likely-recurring`, `amount-changed`, `new`, `one-off`. A coding is
proposed only for **posted** charges labelled `recurring` that have a coding rule. Everything else
is left for a person, with the reason.

**The review CSV** (`output/<month file name>.recurring-review.csv`)

The file accounting checks. It is **not** a QuickBooks import file: the coding columns are proposals
a person accepts or changes, and the import format isn't known yet.

*Which rows:* every charge in the month **except** those labelled `one-off`. Travel, meals, events,
refunds and unrecognised descriptors are left out. They are still in the JSON.

*Row order:* by label, so the ones that need a person come first (`amount-changed`, `new`,
`likely-recurring`, then `recurring`), then by vendor, then by date.

*Columns, in order:*

| # | Column | From | Contents |
|---|---|---|---|
| 1 | `label` | inferred | `amount-changed`, `new`, `likely-recurring` or `recurring` |
| 2 | `coding_status` | inferred | `proposed` (a coding is filled in), `needs-human` (a person decides), or `waiting-for-post` (pending; coded once it settles) |
| 3 | `vendor` | inferred | vendor id from `context/vendors.yaml`, e.g. `aws` |
| 4 | `merchant_descriptor` | CSV | the raw descriptor, e.g. `AWS EMEA aws.amazon.co` |
| 5 | `amount` | CSV | two decimals; positive is a charge |
| 6 | `currency` | CSV | e.g. `USD` |
| 7 | `transaction_date` | CSV | `YYYY-MM-DD` |
| 8 | `status` | CSV | `posted` or `pending` |
| 9 | `card_last4` | CSV | last four digits of the card |
| 10 | `cardholder` | CSV | name the card is under, which isn't necessarily who spent it |
| 11 | `account` | inferred | proposed account number; blank unless `coding_status` is `proposed` |
| 12 | `class` | inferred | proposed class; blank unless `proposed` |
| 13 | `department` | inferred | proposed department; blank unless `proposed` |
| 14 | `entity` | inferred | proposed entity; blank unless `proposed` |
| 15 | `months_seen` | inferred | earlier months the vendor was charged, space-separated, e.g. `2026-07 2026-08` |
| 16 | `reason` | inferred | why it isn't coded, or for a proposed coding, why it was labelled recurring |
| 17 | `transaction_id` | CSV | ties the row back to the export and to the JSON |

"From CSV" columns are copied from the export unchanged. "Inferred" columns are what the Cog worked
out. Columns 11–14 currently come from **invented** coding rules, so they show the shape of a coding,
not a real one.

**Running it** (from `cogs/recurring-subscription-auto-coder-cog/`):

```
pixi run demo                                            # on the synthetic fixtures
pixi run code sept.csv --history jul.csv aug.csv         # on your own files
pixi run test
```

---

**What's shared, and how**

Copied unchanged from the auto-coder into the chase-list builder:

- `src/cog_transactions/`
- `context/transaction.schema.json`
- `context/vendors.yaml`

Change them in one Cog, then copy them to the other. Nothing checks that the copies match yet; that
test comes when the chase-list builder is built.

---

**Not built yet**

- Model step (left until last; where the model runs is undecided)
- Pending -> posted matching across exports taken a few days apart
- Accuracy against accounting's real codings (needs real data)
- The whole chase-list builder
