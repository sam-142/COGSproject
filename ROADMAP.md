# Roadmap

How we get from two empty Cog folders to two working Cogs. Scope is the OpenTeams Brex card only:
10 cards, 60–80 transactions a month, about three quarters of them recurring software charges
(`cogs/questions.md`).

## Where we are

Both Cogs run end to end on **Brex's real export layout**, with no model step. One real export
(89 rows, one month) has been profiled and used; everything is tested on synthetic data in the same
layout.

| | Recurring subscription auto-coder | Chase-list builder |
|---|---|---|
| Runs end to end | yes | yes |
| Reads the real Brex export | yes: 22 of 70 columns | yes: same shared reader |
| Main output | QuickBooks file in accounting's nine fields, plus a review CSV | drafts for review, chase list, chase log |
| `COG.md` + manifest | yes | yes |
| Tests | 96 passing, 3 known gaps (`xfail`) | 76 passing |
| Context files | **empty defaults**; real ones via `--context` | **empty defaults** (vendors, cards); placeholder policy |
| Evaluation | not built | not built |
| Model step | not built, deliberately last | not built, deliberately last |

## Next up, in order

1. **Get the open answers from accounting** (Phase 0).
2. **Chase-list builder: read replies back in** (Phase 4).
3. **Fix the three auto-coder gaps** the test cases exposed (Phase 2).
4. **Evaluation scripts** for both Cogs, against synthetic answer keys.
5. **Write the real-data runbook** (Phase 5).
6. **Commit** regularly; a lot of work is uncommitted.

---

## Phase 0: Groundwork

- [x] `.gitignore` for real statements, exports, outputs, the chase log, and a `private/` folder.
- [x] `private/` blocked from Claude (`.claude/settings.json`), and the rule written into `CLAUDE.md`.
- [x] Decided: every Cog is a pixi package, and pixi tasks are its interfaces.
- [x] Decided: target pixi only for now; Collab (Apollo) deferred.
- [x] A real Brex CSV export received, profiled with `tools/profile_export.py`, and used.
- [x] QuickBooks fields known: DATE, REF NO., TYPE, PAYEE, ACCOUNT, MEMO, CLASS, DEPARTMENT, CHARGE.
- [ ] **Still to ask accounting:**
  - **more months** of exports (3–6; 12 catches annual subscriptions);
  - whether the account on each Brex charge is one **they chose**, or one Brex filled in;
  - where **class and department** come from, since Brex doesn't have them;
  - whether Brex can export **pending** charges (the one export had none);
  - whether **`User`** is the person who spent, or the card's owner, on shared cards;
  - the **direct-debit list**, and subscriptions that renew annually;
  - for the chase-list builder: the **cards, their users and channels**; what counts as **enough
    information** for a charge; the **reply format** they'd want;
  - TYPE wording and REF NO. format: check `quickbooks.yaml` against what they actually type;
  - optionally: whether a hosted model that only ever sees merchant names would be acceptable.
- [ ] **Pick a license** for both Cogs and add it to their `COG.md` frontmatter.

---

## Phase 1: Transaction shape and reading exports

Shared by both Cogs, by copying, not by depending on one another.

- [x] The transaction shape: `parsed` (only what the export says) and `inferred` (everything worked
  out, each value naming its source). A field can't be in both: the schema rejects it and
  `shape.infer()` refuses to write it.
- [x] `context/transaction.schema.json`, plus each Cog's output schema and output example.
- [x] Reading Brex's CSV export (`cog_transactions/load.py`), trimmed to the 22 columns used. A bad
  row is listed with its reason and the run carries on; a missing required column stops it.
- [x] Merging exports of any length and linking pending charges to posted ones
  (`cog_transactions/combine.py`). A match not given by the export is marked as inferred and
  flagged.
- [x] Strict mode with no model, and a `binding` field on every result (`null` until a model step
  exists).
- [x] Test cases in `sample-data/`, one folder per case, including injection, copied into each Cog.
  Tests fail if a copy drifts.

**Exit check:** the reader handles the real export (done: header matches, dates and amounts read).
Per-field read accuracy on real data is still to be reported (rates only, never rows).

---

## Phase 2: Recurring subscription auto-coder

- [x] `COG.md` and manifest (`cog.yaml`).
- [x] Lookup data in `context/` (YAML); org context for a model in `frames/` (Markdown).
- [x] Recurring charges spotted with no model: compared with earlier months, labelled `recurring`,
  `likely-recurring`, `amount-changed`, `new` or `one-off`, with every reason it counts as a
  subscription recorded.
- [x] Usage-billed vs fixed-price vendors: usage amounts may vary (a change over ±10% is flagged);
  fixed-price changes go to a person. Merchants not on the vendor list found through Brex's
  Merchant Name and Category.
- [x] A QuickBooks entry (DATE, REF NO., TYPE, PAYEE, ACCOUNT, MEMO, CLASS, DEPARTMENT, CHARGE) for
  every posted subscription charge; ACCOUNT from the Brex charge unless a coding rule overrides it;
  blank fields don't block an entry.
- [x] Review CSV for accounting, full JSON output, expected-but-missing list.

**Before real data:**

- [ ] **Fix the three known gaps.** Each has an `xfail` test that defines the fix:
  - a subscription cancelled months ago is reported missing forever (`long-history`);
  - two identical charges on the same day are both coded (`double-charge`);
  - a later month passed as history counts as evidence (`history-order`).
- [x] **No invented data in the defaults.** Context files are empty; the invented ones are test data.
- [x] Real context via an override folder (`--context`), and `tools/vendors_to_yaml.py` for a real
  vendor list.
- [ ] **Evaluation script** (`pixi run eval`), built against a synthetic answer key. It reports:
  - accuracy per QuickBooks field (PAYEE, ACCOUNT, CLASS, DEPARTMENT) against what accounting
    actually entered;
  - wrong values, which cost more than blanks;
  - the share of entries flagged for review;
  - coverage: of the charges accounting treated as subscriptions, how many the Cog found.

  Any rules must be built from different months than the ones evaluated.

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

- [x] Real files go in `private/`, which is gitignored. Never in `sample-data/` or a Cog's fixtures.
- [x] Match the real export: the reader reads Brex's 70-column layout, keeps 22 columns, reads
  `MM/DD/YYYY` dates and plain amounts, and maps `Payment Status`. Copied to both Cogs.
- [x] Rebuild the synthetic test cases in the real layout, with a test that dropped columns never
  reach an output.
- [x] An override folder for real context files (`--context`), and a converter for a vendor list.
- [ ] Real context files, in `private/context/`:
  - the vendor list (with `billing: fixed` for fixed-price subscriptions);
  - coding rules, if accounting wants to override Brex's account or add class and department;
  - known recurring from the direct-debit list;
  - cards, users and channels.
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
- [ ] **Auto-coder:** possibly suggest CLASS and DEPARTMENT for blank fields, or a vendor for an
  unrecognised merchant, always marked as a suggestion.
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
- Importing into QuickBooks: the QuickBooks file is for a person to enter or paste from. How
  accounting gets transactions into QuickBooks (by hand, assumed) isn't automated.
- Chase bank statements: they arrive cut off, which accounting has set aside as a separate
  discussion.
- OSbig, Quansight and other entities.
