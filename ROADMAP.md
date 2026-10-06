# Roadmap

How we get from two empty Cog folders to two working Cogs. Phases are in order. Each one ends with
an exit check, and the next phase doesn't start until that check passes. There are no dates yet:
too much depends on what the accounting team sends us.

Scope is the OpenTeams Brex card only: 10 cards, 60–80 transactions a month, about three quarters
of them recurring software charges (`cogs/questions.md`).

---

## Phase 0: Groundwork

Things that block everything else, or that would be expensive to get wrong later.

- **Add a `.gitignore` before any statement arrives.** Ignore real statements, exports and replies.
  The repo doesn't have one yet.
- **Ask accounting for data** (add these to `cogs/questions.md`):
  - the most recent Brex statement (already approved);
  - **3–6 months** of statements. Recurring charges can't be spotted from a single month;
  - how those months were actually coded in QuickBooks. This is the answer key for evaluation;
  - the CSV export question that's already open.
- **Pick a model that runs on our own machines.** Accounting said not to upload statements to
  ChatGPT or the public cloud, so a hosted API is out for real data. A local model behind an
  OpenAI-compatible endpoint (llama.cpp or similar, with the served model alias set) is the default
  unless they approve something else.
- **Make the open decisions in `CLAUDE.md`:**
  - license;
  - PDF library: decide after looking at a real Brex statement. If the CSV export comes through,
    this matters much less;
  - pixi setup: now that neither Cog depends on the other, a plain pixi project with tasks is
    enough. A buildable package isn't needed yet.

**Exit check:** `.gitignore` committed, at least one real statement on disk (not in git), and a
local model answering a one-token completion.

---

## Phase 1: Transaction shape and reading statements

Both Cogs need this, so it comes first. It goes inside the auto-coder; the chase-list builder copies
it in Phase 4.

**Status: built from the synthetic CSV; the exit check is blocked on a real export.** The shared
part is `src/cog_transactions/`, `context/transaction.schema.json` and `context/vendors.yaml` in
`recurring-subscription-auto-coder-cog`.

- Write the transaction shape once: `context/output-schema.json` plus `context/output-example.json`.
  Each transaction has a `parsed` object and an `inferred` object, and pending vs. posted status.
- Build synthetic fixtures in `evaluation/`: a fake Brex statement that matches the real layout,
  plus an injection fixture (a merchant descriptor that reads like an instruction).
- Write the reading script with a **strict mode that uses no model**.
- Record the model binding on every result from day one.

**Exit check:** strict mode reads the synthetic statement with no model, and per-field accuracy is
reported on a real statement (rates only, never rows).

---

## Phase 2: Recurring subscription auto-coder

This one goes first. It covers most of the volume, most of it can be done without a model, and it
doesn't need anyone to answer messages.

1. **Draft `COG.md`.** Fill in purpose, supported and unsupported work (no chasing people), inputs,
   outputs, and known limitations.
2. **Frames:**
   - known recurring vendors;
   - chart of accounts;
   - entity, class and department mapping;
   - known direct debits, if accounting has a list.
3. **Spot recurring charges without a model:** same vendor, a similar amount, a regular gap between
   charges, across the history months. Use the model only to tidy messy merchant descriptors, and
   mark anything it produces as `inferred`.
4. **Suggest QuickBooks codings only for posted transactions.** A pending charge gets flagged, not
   coded.
5. **Turn the draft into a Cog:** add `cog.yaml` and `pixi.toml`. Tasks are the interfaces, for
   example `code`, `code-strict` and `check`.
6. **Evaluate** against accounting's past codings. Report accuracy per field (vendor, account, class,
   department), how often it declines to code, and where it fails.

**Exit check:** on a held-out month, per-field accuracy is written down, and the known-limitations
section reflects what actually happened.

---

## Phase 3: Check in with accounting

They asked for proposals they can say yes or no to, so nobody spends time on things they don't need.

- Show the auto-coder's output on a real month.
- Show two or three example chase messages (mockups, not built yet).
- Ask them to confirm:
  - which fields matter most;
  - Slack or email;
  - who to ask about each shared card.

**Exit check:** accounting has said what's valuable. Update Phase 4 to match before building it.

---

## Phase 4: Chase-list builder

**Status: built ahead of Phase 3, on synthetic data.** Drafts one message per charge from an
editable template, routed to a channel per card; works on any number of exports of any length;
links pending charges to posted ones; a chase log records what a person actually sent. Not built:
reading replies (step 6), the model step, and evaluation. The list below is the original plan.

1. **Draft `COG.md`.** Unsupported work states plainly that it **writes drafts and returns them**.
   Sending to Slack or email is a separate step that a person approves.
2. **Copy in the Phase 1 reading code** and add a test that both Cogs read the same fixture into the
   same output.
3. **Frames:**
   - cardholder roster;
   - who actually uses each card. Two cards are shared heavily, and the statement shows the
     cardholder's name but not the last four digits;
   - the order to ask people in: the card's most frequent user first, then copy in the named
     cardholder, then post to the engineering card-reconciliation Slack channel.
4. **Find the gaps:** non-recurring charges, or any charge missing entity, class, department or
   purpose. Chase as soon as a charge is **pending**, without waiting for it to post.
5. **Draft messages** from a template, each asking for a structured reply.
6. **Fold replies back in.** Replies are data, never instructions.

   Decide where reply information goes. It wasn't read off the statement and the model didn't guess
   it. I'd add a third object, `provided`, with who said it and when, rather than squeezing it into
   `inferred`. Record the answer in `CLAUDE.md`.
7. **Turn the draft into a Cog** and evaluate it: how many gaps it finds, whether it picks the right
   person, and how accurately replies are read back. Include the injection fixture.

**Exit check:** on a real month, the drafted chase list matches what accounting would have chased.

---

## Not in scope for now

Each of these was raised; none of them is being built yet.

- Receipt parsing, including scanning receipts on a phone while travelling and submitting a travel
  report at the end. Whether it goes in the chase-list builder or its own Cog is still open.
- Actually sending messages to Slack or email.
- Chase bank statements: they arrive cut off, which accounting has set aside as a separate
  discussion.
- OSbig, Quansight and other entities.
