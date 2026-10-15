# COG implementation

**This is where the implementations for the cogs Chase-List Builder and Recurring subscription auto-coder live**,

---

Each Cog is a folder with a `COG.md` (what it does, for people), a `cog.yaml` manifest, a `pixi.toml` (its commands), its code in `src/`, its context in `context/` and `frames/`, and its tests and test data in `tests/` and `evaluation/`. These COGS are built by referencing (but not bound by) the cogspec (SPEC.md) written by Trent Oliphant.

---

**Hurdles**

Here are some things I think it is worth keeping in mind during development:

**Pending transactions**

Card transactions appear pending with a provisional amount and a descriptor that often changes on settlement two to four days later. At a 3-day cadence we will see both states constantly. Proposed solution: chase on pending, code on posted. Chasing early is better because people remember what they bought on Tuesday, not three weeks ago, but never propose a QuickBooks coding off an amount that can still change. Most aggregators give you a link from the posted transaction back to its pending ID; if yours doesn't, match on card, merchant and date proximity and mark the link as inferred.

---

**Current Architecture:**

Two independent Cogs, each its own pixi package. There is no shared parsing Cog: the part both need
(reading Brex exports into one transaction shape) is **copied** between them unchanged, and the
chase-list builder's tests fail if the copies differ.

| Cog | Status |
|---|---|
| `recurring-subscription-auto-coder-cog` | runs end to end, on synthetic data and on Brex's real export layout; writes the QuickBooks file; no model step; 96 tests (+3 known gaps marked `xfail`) |
| `chase-list-builder-cog` | runs end to end the same way; drafts one message per charge from a template; reading replies not built; no model step; 76 tests |

Neither Cog ships with real or invented data in its defaults: the lookup files in `context/` are
empty. Real ones go in an override folder (`--context`) outside the repo; the invented ones the
tests and demos use live in `sample-data/context/`.

---

**Recurring subscription auto-coder**

```
recurring-subscription-auto-coder-cog/
  COG.md              what the Cog does and doesn't do
  cog.yaml            manifest: interfaces, where context lives
  pixi.toml           environment + tasks (the Cog's commands)
  pyproject.toml      makes src/ installable

  src/cog_transactions/   SHARED - identical in both Cogs
    load.py               Brex CSV -> transactions; keeps 22 of the 70 columns
    shape.py              the transaction shape and its rules
    vendors.py            merchant -> vendor: the vendor list, else Brex's Merchant Name and Category
    combine.py            merging exports, linking pending charges to posted ones

  src/auto_coder/         this Cog only
    cli.py                commands: code, check, use
    core.py               runs the steps in order, builds the run record
    context.py            loads context files; the override folder
    recurrence.py         labels each charge, and records why it counts as a subscription
    coding.py             builds the QuickBooks entry for each subscription charge
    report.py             writes the QuickBooks file, the review CSV, the JSON, the summary
    model.py              model settings + one-token test (not used by the pipeline yet)

  context/
    vendors.yaml              SHARED. Vendor list: empty by default
    known-recurring.yaml      known recurring charges: empty by default
    coding-rules.yaml         optional per-vendor overrides for PAYEE, ACCOUNT, CLASS, DEPARTMENT: empty
    chart-of-accounts.yaml    what a rule may use: empty
    quickbooks.yaml           how entries are written (TYPE wording, date format, REF NO.): settings
    transaction.schema.json   SHARED. The transaction shape
    output-schema.json        the full output contract
    output-example.json       a short real output

  frames/             Markdown org context for the model (nothing reads it yet)
  evaluation/fixtures/   test cases copied from sample-data/, plus the invented context
  tests/                 96 tests
```

**How a run flows:**

```
Brex CSV for the month + Brex CSVs for earlier months
  -> load        parsed: the 22 columns used, exactly as the export says
  -> vendors     inferred.vendor       (vendor list, else Brex's Merchant Name + Category)
  -> recurrence  inferred.recurrence   (label, why it's a subscription, amount flags)
  -> coding      inferred.coding       (the QuickBooks entry, field by field)
  -> report      output/<name>.quickbooks.csv
                 output/<name>.recurring-review.csv
                 output/<name>.recurring.json
```

Every transaction has a `parsed` object (read from the export) and an `inferred` object (worked out
afterwards, each value naming its source). A field can't be in both: the schema rejects it and the
code refuses to write it.

Recurrence labels: `recurring`, `likely-recurring`, `amount-changed`, `new`, `one-off`. Every posted
charge with one of the first four labels becomes a QuickBooks entry; the last three are also
flagged for review. Usage-billed vendors (the default) may vary in amount; a change over ±10% is
flagged, not blocked. Fixed-price vendors send a change to a person.

**The QuickBooks file** (`output/<month file name>.quickbooks.csv`)

One row per posted subscription charge, in exactly the fields accounting enters into QuickBooks:

```
DATE,REF NO.,TYPE,PAYEE,ACCOUNT,MEMO,CLASS,DEPARTMENT,CHARGE
09/01/2026,4417,Credit Card Expense,Amazon Web Services,Expenses:6120 Cloud Hosting,,,,1843.27
```

| Column | Filled from |
|---|---|
| DATE | transaction date, `MM/DD/YYYY` |
| REF NO. | Brex `Last 4`: the card the charge was on; blank if none |
| TYPE | `Credit Card Expense` (`Credit Card Credit` for a credit); wording set in `quickbooks.yaml` |
| PAYEE | a coding rule, else Brex `Integration Vendor`, else Brex `Merchant Name` |
| ACCOUNT | a coding rule, else the account already on the Brex charge, by its fully qualified name (`Integration Debit Line Category Fully Qualified Name`) |
| MEMO | Brex `Memo` |
| CLASS | a coding rule, else Brex `Integration Class` |
| DEPARTMENT | a coding rule, else Brex `Integration Department` |
| CHARGE | the amount |

**Blank fields don't hold a row back.** With real Brex data and no coding rules, ACCOUNT is filled
from Brex and CLASS and DEPARTMENT are blank (Brex doesn't have them). Only the transaction itself
keeps a charge out: pending, declined, or not a subscription.

**The review CSV** (`output/<month file name>.recurring-review.csv`)

Every subscription charge, with what to check. Columns, in order:

| # | Column | Contents |
|---|---|---|
| 1 | `label` | `amount-changed`, `new`, `likely-recurring` or `recurring` |
| 2 | `quickbooks` | `ready` (in the QuickBooks file) or `waiting-for-post` (pending) |
| 3 | `review` | what a person should check, if anything: a new vendor, one month of history, an amount that moved |
| 4 | `vendor` | vendor id: from the vendor list, or made from Brex's Merchant Name |
| 5 | `merchant_name` | Brex `Merchant Name` |
| 6 | `merchant_descriptor` | Brex `Statement Descriptor` |
| 7 | `amount` | two decimals |
| 8 | `currency` | e.g. `USD` |
| 9 | `change_vs_last` | e.g. `+34.6% vs 520.00 (2026-08)` |
| 10 | `transaction_date` | `YYYY-MM-DD` |
| 11 | `status` | `posted` or `pending` |
| 12 | `card_last4` | Brex `Last 4` |
| 13 | `cardholder` | Brex `User` |
| 14 | `account` | the entry's ACCOUNT |
| 15 | `account_from` | `rule` or `export` (the Brex charge) |
| 16 | `class` | the entry's CLASS |
| 17 | `department` | the entry's DEPARTMENT |
| 18 | `blank_fields` | which QuickBooks fields are blank, e.g. `MEMO CLASS DEPARTMENT` |
| 19 | `months_seen` | earlier months the vendor was charged |
| 20 | `reason` | **why it counts as a subscription**: every piece of evidence that applies, joined with `; `. Any of: on the vendor list as a subscription (with its billing); Brex category; on the known-recurring list; charged in N earlier months (naming them); same amount (±10%) in N earlier months (fixed-price only). E.g. `Brex category: Recurring software & SaaS; charged in 2 earlier months (2026-07, 2026-08)` |
| 21 | `transaction_id` | Brex `Id`; ties the row to the QuickBooks file and the JSON |

**Running it** (from `cogs/recurring-subscription-auto-coder-cog/`):

```
pixi run demo                                            # synthetic data and synthetic context
pixi run code sept.csv --history jul.csv aug.csv         # your own files
pixi run code sept.csv --history jul.csv aug.csv --context <folder>   # with real context files
pixi run test
```

`--history` takes several files, or repeat the flag. The summary starts by saying which months the
history covers. For real data, see the root `README.md`: everything stays in `private/`.

---

**Chase-list builder**

```
chase-list-builder-cog/
  COG.md              what the Cog does and doesn't do, and where a person approves
  cog.yaml            manifest: interfaces (draft, sent, demo), where context lives
  pixi.toml           environment + tasks

  src/cog_transactions/   SHARED - identical to the auto-coder's copy
  src/chase_list/
    cli.py                commands: draft, sent
    core.py               runs the steps in order, builds the run record
    context.py            loads and checks cards, policy, template, vendors
    select.py             routes each charge to its card's channel; decides whether to chase it
    draft.py              fills the message template, defusing Slack mentions
    log.py                the chase log: what a person has actually sent
    report.py             writes JSON, chase-list CSV, drafts for review

  context/
    cards.yaml                card -> channel, cardholder, users: empty by default
    chase-policy.yaml         what's chased, what each message asks (placeholder settings)
    message-template.md       the wording of every message; editable, see context/README.md
    vendors.yaml              SHARED. Empty by default
    transaction.schema.json   SHARED
    output-schema.json, output-example.json

  frames/chasing.md       how chasing works at OpenTeams, for a model (nothing reads it yet)
  evaluation/fixtures/    test cases copied from sample-data/, plus the invented cards and vendors
  tests/                  76 tests, including checks that the shared copies match
```

**How a run flows, and where a person approves:**

```
exports (any number, any length, may overlap)
  -> read, merge, drop duplicates
  -> identify vendors
  -> link pending charges to the posted charges that replaced them
  -> route to the card's channel        (context/cards.yaml)
  -> decide: draft / needs-routing / already-chased / skip
  -> fill the template for each charge  (context/message-template.md)
  -> output/chase_<from>_to_<to>.chase.json, .chase-list.csv, .drafts.md
       |
  a person reviews the drafts and sends the ones they want        <- approval
       |
  pixi run sent <the .chase.json>  records them in the chase log  <- approval
```

The Cog never sends anything. A charge counts as chased only after `pixi run sent`, so a draft
nobody sent comes back next run, and one that was sent never does, even when its pending charge
reappears as posted with a different amount.

**Running it** (from `cogs/chase-list-builder-cog/`):

```
pixi run draft export.csv [more.csv ...] --coded <auto-coder .recurring.json> [--context <folder>]
pixi run sent output/chase_<from>_to_<to>.chase.json
pixi run demo                    # synthetic data and synthetic cards
pixi run test
```

---

**What's shared, and how**

Copied unchanged between the two Cogs:

- `src/cog_transactions/`: `load.py` (reading and trimming Brex exports), `shape.py`, `vendors.py`,
  and `combine.py` (merging exports, linking pending charges to posted ones)
- `context/transaction.schema.json`
- `context/vendors.yaml` (empty by default)
- `evaluation/fixtures/injection/`

Change them in one Cog, then copy them to the other. The chase-list builder's tests fail if any
shared file differs from the auto-coder's copy.

---

**Not built yet**

- Chase-list builder: reading replies back into the transactions
- Evaluation for both Cogs (needs accounting's real decisions to compare against)
- Model steps in both Cogs (left until last; where the model runs is undecided)

See `ROADMAP.md` for the full list.
