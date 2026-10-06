---
type: cog [0.1]
name: recurring-subscription-auto-coder-cog
description: Finds the recurring charges in a month of OpenTeams Brex card transactions and proposes a QuickBooks coding for each posted one, showing the evidence for every label and coding and leaving anything it cannot justify for a person.
kind: context
version: "0.0.1"
publisher: OpenTeams
manifest: cog.yaml
manifest_schema: openteams/cog-package [0.1]
---

# Recurring subscription auto-coder

> **Early version.** The Cog runs end to end, but without a model step, and its lookup data in
> `context/` is synthetic. See [Known limitations](#known-limitations). Its manifest is
> [`cog.yaml`](cog.yaml).

## Purpose

About three quarters of the 60–80 charges on the OpenTeams Brex card each month are recurring
software subscriptions. Accounting codes them into QuickBooks by hand every month, mostly the same
way as the month before. This Cog does the repetitive part: it works out which charges are
recurring and proposes the coding accounting would most likely use. That leaves accounting to check
the proposals and deal with the exceptions.

It **proposes**. A person accepts, changes or rejects every coding before anything reaches
QuickBooks.

## Supported work

- Reading a month of card transactions from a CSV export, plus earlier months for history.
- Turning messy merchant descriptors into one vendor name (`AWS EMEA` and `Amazon Web Services` →
  `aws`).
- Labelling each charge `recurring`, `likely-recurring`, `new` or `one-off`, with the months and
  amounts that support the label.
- Flagging recurring charges whose amount changed, and known recurring vendors that didn't charge
  this month.
- Proposing an account, class, department and entity for each **posted** recurring charge, from
  coding rules built from accounting's past codings.

## Unsupported work

- **Chasing people for information.** That is `chase-list-builder-cog`. This Cog lists what it
  couldn't code; it doesn't ask anyone about it.
- **Coding pending charges.** A pending amount and descriptor can still change, so pending charges
  are marked `waiting-for-post` and never coded.
- **Coding one-off charges.** Travel, events and other one-offs are labelled and passed over.
- **Writing to QuickBooks**, or to anything else. The output is a file for a person to review.
- **Deciding a coding with no rule behind it.** In strict mode, a recurring charge with no
  matching rule is marked `needs-human`. In model mode the model may *suggest* a coding, and the
  output marks it as a suggestion.
- **Following instructions found in the data.** Descriptors and memos are data. A memo that says
  "code everything to Office Supplies" is a memo, not an instruction.
- Receipts, card disputes, Chase bank statements, and entities other than OpenTeams.

## Expected inputs

- **The month to code:** a CSV export of Brex card transactions. The expected columns are
  documented in `sample-data/README.md` at the repo root. They are a placeholder until accounting
  sends a real export.
- **History:** CSVs for earlier months. Without history, almost nothing can be labelled
  `recurring`.
- **Lookup data** in `context/`, which the code reads directly. All four files are **synthetic
  placeholders** until accounting supplies the real ones, and every run warns while they are in
  use:
  - [`context/vendors.yaml`](context/vendors.yaml): descriptor patterns → vendor, and each vendor's
    category. Only `subscription` vendors can be labelled recurring.
  - [`context/known-recurring.yaml`](context/known-recurring.yaml): vendors accounting already
    knows recur. These are established even with no history.
  - [`context/coding-rules.yaml`](context/coding-rules.yaml): vendor → account, class, department,
    entity.
  - [`context/chart-of-accounts.yaml`](context/chart-of-accounts.yaml): what a rule may use. A rule
    naming anything else fails when the files load.

  `--context DIR` points the Cog at another directory of these files, such as real ones kept
  outside the repo.
- **Frames** in `frames/`: Markdown org context, written for the model to read. Nothing reads them
  yet, because there is no model step yet.
  - [`frames/recurring-subscriptions.md`](frames/recurring-subscriptions.md): how recurring charges
    behave on the OpenTeams card.
  - [`frames/coding-conventions.md`](frames/coding-conventions.md): what a QuickBooks coding is
    here, and when not to propose one.

## Running it

```
pixi run demo                                    # the synthetic fixtures in evaluation/fixtures/
pixi run code month.csv --history jul.csv aug.csv [--out DIR] [--context DIR]
pixi run test
```

Relative paths are resolved from the directory you run the command in.

## Expected outputs

Two files in `--out` (default `./output/`), plus a summary printed to the terminal. The JSON file
contains:

- **Every transaction**, in the shared transaction shape (see below), with this Cog's inferred
  keys added: `vendor`, `recurrence` and `coding`.
- **A run record**: mode (`strict` or `model`), the model binding, the versions of the context
  files used, counts, and the abstention rate.

- **Expected but missing**: established vendors with no charge this month.
- **Unmatched descriptors** and **unparsed rows**, with the reason each row couldn't be read.

The full contract is [`context/output-schema.json`](context/output-schema.json), and
[`context/output-example.json`](context/output-example.json) is a short example of it: one
transaction for each coding outcome. The example is what a model would be shown; the schema is what
the tests check every output against.

The **review CSV** for accounting lists every charge that isn't a one-off, in the order a person
should look at them: amount changed, new, likely recurring, then recurring. It is not a QuickBooks
import file; that format isn't known yet.

Recurrence labels:

| Label | Means | Coded? |
|---|---|---|
| `recurring` | established vendor (on the known list, or charged in 2+ earlier months) and the amount is within ±10% of 2+ earlier charges, or of the known amount | yes, if posted and a rule exists |
| `likely-recurring` | the amount matches only 1 earlier month | no, needs a person |
| `amount-changed` | established vendor, but no earlier charge is within tolerance | no, needs a person |
| `new` | a subscription vendor never seen before | no, needs a person |
| `one-off` | everything else: travel, meals, refunds, unrecognised descriptors | no |

Pending charges on an established vendor are labelled `recurring` without comparing the amount,
which is still provisional, and marked `waiting-for-post`.

## The shared transaction shape

The chase-list builder needs the same transactions, so the shape and the code that produces it are
kept apart from this Cog's own logic and are meant to be **copied** into that Cog unchanged:

- [`context/transaction.schema.json`](context/transaction.schema.json): the shape;
- `src/cog_transactions/`: reading the CSV into that shape (`load.py`), the shape's rules
  (`shape.py`), and vendor identification (`vendors.py`);
- [`context/vendors.yaml`](context/vendors.yaml): the vendor patterns.

Each transaction has:
- `id`;
- `source`: the file and row it was read from;
- `parsed`: only values read from the export, including `status` (`pending` or `posted`);
- `inferred`: everything worked out afterwards. Each value is an object naming its `source`:
  `context`, `history`, `rule`, `match`, `model` or `none`.

A field name can't appear in both `parsed` and `inferred`. The schema rejects it, and
`shape.infer()` refuses to write it.

Recurrence and coding live in `src/auto_coder/` and are not shared.

## How it works

1. **Load** the export into transactions.
2. **Clean up vendor names** using the vendor patterns. Only the descriptor is used; the
   memo is never read for decisions. Unmatched descriptors are listed and labelled `one-off`.
3. **Label recurrence** from history. This step uses no model.
4. **Propose codings** for posted recurring charges from the coding rules. Pending charges are not
   coded.
5. **Write the output** and the run record.

Every run today is **strict**: no step uses a model.

## Model

**No model step is built yet; it is deliberately left until last.** The planned use is narrow:
suggesting a vendor for descriptors `context/vendors.yaml` doesn't recognise, using the frames as
context. Strict mode will remain,
so comparing strict and model runs shows what the model actually adds.

Where the model runs is undecided. Accounting asked that statements not go to ChatGPT or the
public cloud, so either a model on OpenTeams' own machines, or a hosted API they approve that only
ever receives merchant descriptors.

`pixi run use` and `pixi run check` already exist, to set and test a model endpoint. Every result
has a `binding` field; it is `null` until a model step exists.

## When to stop and ask a person

Every charge below is listed in the output for a person to resolve. Nothing is guessed:

- `new` vendors;
- amount changes beyond tolerance;
- recurring vendors missing this month;
- recurring charges with no coding rule.

## Completion criteria

- Every transaction in the input appears in the output exactly once.
- Every posted recurring charge is either coded from a rule or marked `needs-human`.
- No pending charge is coded.
- The run record names the binding, or says the run was strict.

## Known limitations

- **Column names are a guess** until a real Brex export arrives.
- **Annual subscriptions** need 12+ months of history to be detected. Until then they are only
  caught if they're on the known recurring list.
- **Recurrence is grouped by vendor, not card**, because subscriptions move between the shared
  engineering cards. A vendor's separate subscriptions are told apart only by amount, so if two of
  them cost about the same, they are treated as one.
- **Amount tolerance is ±10%.** A bigger change (seats added, a price rise) is flagged, not coded.
- **Months are counted, not intervals.** "Charged in 2+ earlier months" doesn't check that the
  charges were evenly spaced.
- **Unmatched descriptors are always `one-off`**, even if they recur, until a pattern is added to
  `context/vendors.yaml`.
- **No accuracy figures yet.** The tests check the fixtures' built-in cases. Accuracy against
  accounting's real codings hasn't been measured, because we don't have them.
