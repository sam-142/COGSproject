# Roadmap

How we get from two empty Cog folders to two working Cogs. Scope is the OpenTeams Brex card only:
10 cards, 60–80 transactions a month, about three quarters of them recurring software charges
(`cogs/questions.md`).

## Where we are

Both Cogs run end to end on **synthetic data**, with no model step. Everything that can be built
without accounting's data is either built or listed under "Before real data" below. What's left
after that waits on accounting.

| | Recurring subscription auto-coder | Chase-list builder |
|---|---|---|
| Runs end to end | yes, on synthetic data | yes, on synthetic data |
| `COG.md` + manifest | yes | yes |
| Test cases | 61 passing, 3 known gaps (`xfail`) | 64 passing |
| Context files | **invented**: vendors, coding rules, chart of accounts, known recurring | **invented**: vendors, cards and channels; **placeholder** policy |
| Evaluation | not built | not built |
| Model step | not built, deliberately last | not built, deliberately last |

## Next up, in order

1. **Send accounting the questions** (Phase 0). Everything after "Before real data" waits on their
   answers.
2. **Commit** the test-case work.
3. **Fix the three auto-coder gaps** the test cases exposed (Phase 2).
4. **Stop the auto-coder proposing invented codings** (Phase 2).
5. **Read replies back in** (Phase 4).
6. **Evaluation scripts** for both Cogs, against synthetic answer keys.
7. **Write the real-data runbook** (Phase 5).

---

## Phase 0: Groundwork

- [x] `.gitignore` for real statements, exports, outputs, the chase log, and a `private/` folder.
- [x] Decided: every Cog is a pixi package, and pixi tasks are its interfaces.
- [x] Decided: target pixi only for now; Collab (Apollo) deferred.
- [ ] **Ask accounting for data and answers.** Add these to `cogs/questions.md` and send them:
  - a CSV of the statement they already sent;
  - how easy CSV exports are, and whether a date range (e.g. the last 5 days) can be picked;
  - whether the export includes **pending** charges and the **last four digits** of each card;
  - **3–6 months** of CSVs. Recurring charges can't be confirmed from one month; 12 months catches
    annual ones;
  - **those months' card transactions exported from QuickBooks, as coded** (account, class,
    department, entity). This is both the source of the coding rules and the answer key for
    evaluation. The list of accounts, classes and departments can be taken from it;
  - how card transactions get into QuickBooks today: a bank feed, an imported file, or by hand. A
    screenshot of one entry helps, but doesn't answer this;
  - the direct-debit list, and any subscriptions that renew annually;
  - for the chase-list builder: who uses each card, whether a channel per card works, what counts
    as "enough information" for a charge, and the reply format they'd want;
  - optionally: whether a hosted model that only ever sees merchant names would be acceptable.
- [ ] **Pick a license** for both Cogs and add it to their `COG.md` frontmatter.
- [ ] **PDF library:** only matters if accounting can't export CSVs.

---

## Phase 1: Transaction shape and reading exports

Shared by both Cogs, by copying, not by depending on one another.

- [x] The transaction shape: `parsed` (only what the export says) and `inferred` (everything worked
  out, each value naming its source). A field can't be in both: the schema rejects it and
  `shape.infer()` refuses to write it.
- [x] `context/transaction.schema.json`, plus each Cog's output schema and output example.
- [x] Reading CSVs (`cog_transactions/load.py`). A bad row is listed with its reason and the run
  carries on; a missing column stops it.
- [x] Merging exports of any length and linking pending charges to posted ones
  (`cog_transactions/combine.py`). A match not given by the export is marked as inferred and
  flagged.
- [x] Strict mode with no model, and a `binding` field on every result (`null` until a model step
  exists).
- [x] Test cases in `sample-data/`, one folder per case, including injection, copied into each Cog.
  Tests fail if a copy drifts.

**Exit check, blocked on real data:** the reader handles a real export, and per-field read
accuracy is reported (rates only, never rows).

---

## Phase 2: Recurring subscription auto-coder

- [x] `COG.md` and manifest (`cog.yaml`).
- [x] Lookup data in `context/` (YAML); org context for a model in `frames/` (Markdown).
- [x] Recurring charges spotted with no model: compared with earlier months, ±10% tolerance,
  labelled `recurring`, `likely-recurring`, `amount-changed`, `new` or `one-off`.
- [x] Codings proposed only for posted charges labelled `recurring` that have a rule; everything
  else left for a person, with the reason.
- [x] Review CSV for accounting, full JSON output, expected-but-missing list.

**Before real data:**

- [ ] **Fix the three known gaps.** Each has an `xfail` test that defines the fix:
  - a subscription cancelled months ago is reported missing forever (`long-history`);
  - two identical charges on the same day are both coded (`double-charge`);
  - a later month passed as history counts as evidence (`history-order`).
- [ ] **Stop proposing invented codings.** Empty `context/coding-rules.yaml`, so recurring charges
  show `needs-human` until real rules exist. Keep the coding logic tested with a test-only rules
  file.
- [ ] **Evaluation script** (`pixi run eval`), built against a synthetic answer key. It reports:
  - accuracy per field (account, class, department, entity);
  - wrong proposals, which cost more than no proposal;
  - abstention rate;
  - coverage: of the charges accounting coded as recurring, how many the Cog found.

  Rules must be built from different months than the ones evaluated.

**Exit check, blocked on real data:** on a held-out real month, per-field accuracy is written down
in `evaluation/README.md`, and Known limitations in `COG.md` reflects it.

---

## Phase 3: Check in with accounting

They asked for proposals they can say yes or no to, so nobody spends time on things they don't need.
This can happen now, with synthetic output, and again with real output.

- [ ] Show the auto-coder's review CSV.
- [ ] Show a few chase drafts from `pixi run demo`.
- [ ] Ask them to confirm which fields matter most, Slack or email, and whether one message per
  charge is right or too many.

**Exit check:** accounting has said what's valuable. Adjust both Cogs before going further.

---

## Phase 4: Chase-list builder

Built ahead of Phase 3, on synthetic data.

- [x] `COG.md` and manifest. It drafts and never sends; a person approves every message.
- [x] Shared code copied from the auto-coder, with a test that the copies stay identical.
- [x] Any number of exports of any length; overlapping rows counted once; pending charges linked
  to the posted charges that replaced them.
- [x] Decides per charge: `draft`, `needs-routing`, `already-chased` or `skip`. Chases on pending.
- [x] Routes to one channel per card (`context/cards.yaml`).
- [x] One message per charge, from an editable template; Slack mentions in export text are defused.
- [x] Chase log: a charge counts as chased only after a person runs `pixi run sent`.
- [x] Optional input of the auto-coder's output, to skip what it coded.

**Before real data:**

- [ ] **Read replies back in.** The drafts already end with a fill-in form (`ref:`, `purpose:`,
  `department:`, `receipt:`), so replies in that format can be read with no model.
  - Decide where answers go in the transaction shape. Suggested: a third object, `provided`, with
    who said it and when. This changes the shared shape, so both Cogs get it. Record the decision
    in `CLAUDE.md`.
  - A `pixi run replies` command that matches each reply to its charge by `ref`.
  - A reply injection fixture: replies are the most likely place for one.
  - Replies that ignore the form are left for a person, and later for the model.
- [ ] **Evaluation script**, against a synthetic answer key: did it chase what accounting would
  have, and route it to the right place?
- [ ] **Decide where the chase log lives** if more than one person runs the Cog. Today it's a local
  file, so two people would chase the same charges.

**Exit check, blocked on real data:** on a real month, the chase list matches what accounting would
have chased, sent to the right channels.

---

## Phase 5: Real data arrives

Same steps for both Cogs. Write them up as a checklist (`REAL-DATA.md`) before the data arrives, so
day one is quick.

- [ ] Real files go in `private/`, which is gitignored. Never in `sample-data/` or a Cog's fixtures.
- [ ] Match the real export: column names and formats (dates, amount signs, `$` and thousands
  separators) in `cog_transactions/load.py`. Copy the shared files to the other Cog.
- [ ] Reshape the synthetic test cases to the real format: same columns, still fake data.
- [ ] Rebuild the context files from real data:
  - vendor patterns from real descriptors;
  - coding rules and the chart of accounts from the QuickBooks export;
  - known recurring from the direct-debit list;
  - cards, users and channels.

  Set `status: real`. Ask accounting whether these may live in the repo or in `private/context/`.
- [ ] Fill in the "Placeholders, until accounting confirms" sections of the frames.
- [ ] Run both evaluations on held-out months. Record rates, never rows. These are the exit checks
  for Phases 1, 2 and 4.

---

## Phase 6: Model step (deliberately last)

- [ ] **Decide where the model runs.** Options:
  - a laptop;
  - a shared server on OpenTeams' network;
  - OpenTeams' own cloud account;
  - an approved hosted API.

  Accounting's sign-off is needed for anything that isn't on OpenTeams' machines. Still open: what
  Jev is, and whether it fits here.
- [ ] **Auto-coder:** suggest a vendor for descriptors the vendor list doesn't recognise. Possibly
  suggest a coding for `needs-human` charges, as a suggestion only.
- [ ] **Chase-list builder:** read free-text replies; possibly word drafts more naturally.
- [ ] Send the model only what it needs (merchant names, not cardholders, card numbers or amounts),
  using the output *example*, not the schema.
- [ ] Record the binding on every result; add `model-endpoint/openai-compatible` to each manifest's
  `requires`, and `check` to its interfaces.
- [ ] The injection fixtures are the first thing the model step must pass. Compare strict and model
  runs to measure what the model actually adds.

---

## Not in scope for now

Each of these was raised; none of them is being built yet.

- Receipt parsing, including scanning receipts on a phone while travelling and submitting a travel
  report at the end. Whether it goes in the chase-list builder or its own Cog is still open.
- Actually sending messages to Slack or email.
- A QuickBooks import file, until we know how accounting gets transactions in.
- Chase bank statements: they arrive cut off, which accounting has set aside as a separate
  discussion.
- OSbig, Quansight and other entities.
