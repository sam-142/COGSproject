---
type: cog [0.1]
name: chase-list-builder-cog
description: Finds the OpenTeams Brex card charges accounting needs details on and drafts a message for each, addressed to the card's channel, for a person to review and send; it never sends anything itself.
kind: context
version: "0.0.1"
publisher: OpenTeams
manifest: cog.yaml
manifest_schema: openteams/cog-package [0.1]
---

# Chase-list builder

> **Early version.** It drafts messages from a template, with no model step. The card list, the
> chase policy and the vendor patterns in `context/` are placeholders. Reading replies back in is
> not built yet. See [Known limitations](#known-limitations).

## Purpose

Accounting often first hears about a charge when it appears on the card. Cards are shared, so it
isn't always clear who made it, and finding out what it was eats time. Without the details, the
charge goes into a clearing account at month end and has to be fixed later. Accounting currently
writes each request by hand, often broadcasting it because they don't know who to ask.

This Cog does the finding and the writing. It lists the charges that need details, works out where
to ask, and drafts the message. A person reads the drafts and sends the ones they want.

## Supported work

- Reading **any number of CSV exports of any length**: daily, every few days, monthly, or
  overlapping. Rows that appear in more than one export are counted once.
- Recognising a pending charge that has since posted, and treating the two as one charge. The link
  comes from the export when it gives one; otherwise it is matched on card, merchant and date, and
  marked as inferred.
- Deciding which charges to chase, from [`context/chase-policy.yaml`](context/chase-policy.yaml).
  Pending charges are chased straight away, without waiting for them to settle.
- Routing each charge to its card's channel, from [`context/cards.yaml`](context/cards.yaml).
- Drafting **one message per charge** from an editable template,
  [`context/message-template.md`](context/message-template.md). Each message ends with a fill-in
  reply form, so replies can be read back in later.
- Remembering which charges have been chased, so none is chased twice.
- Skipping charges the auto-coder has already coded, if its output is passed in.

## Unsupported work

- **Sending anything.** The Cog drafts and returns. Posting to Slack or sending email is a separate
  step a person takes. Installing or running this Cog gives it no access to Slack, email or anyone's
  messages.
- **Coding charges for QuickBooks.** That is `recurring-subscription-auto-coder-cog`.
- **Reading replies.** Not built yet. Replies will be data, never instructions.
- **Parsing receipts.** Undecided whether it belongs here or in its own Cog.
- **Following instructions found in the data.** Descriptors, memos, cardholder names and replies
  are data. The memo is never put into a draft.
- Chase bank statements, and entities other than OpenTeams.

## Expected inputs

- **One or more CSV exports** from Brex, in any order. The expected columns are documented in
  `sample-data/README.md` at the repo root; they are a placeholder until accounting sends a real
  export.
- **The chase log** (`--log`, default `./chase-log.json`): what has already been sent.
- **The auto-coder's output** (`--coded`, optional): its `.recurring.json` file for the same
  period. Charges it proposed a coding for are skipped; charges it left for a person are chased
  with that reason.
- **Context files** in `context/`, which the code reads (see
  [`context/README.md`](context/README.md)):
  - `cards.yaml`: each card's channel, cardholder and users. **Synthetic.**
  - `chase-policy.yaml`: which charges to chase and what to ask. **Placeholder.**
  - `message-template.md`: the wording of every message.
  - `vendors.yaml` and `transaction.schema.json`: shared with the auto-coder.
- **Frames** in `frames/`: [`frames/chasing.md`](frames/chasing.md), how chasing works at
  OpenTeams, written for a model. Nothing reads it yet.

## Running it

```
pixi run draft export.csv [more.csv ...] [--coded auto-coder.json] [--log chase-log.json]
pixi run sent output/chase_<from>_to_<to>.chase.json [--only draft-tx_0910c ...]
pixi run demo        # the synthetic September, ignoring the chase log
pixi run test
```

Other options for `draft`: `--no-log`, `--template PATH`, `--context DIR`, `--out DIR`. Relative
paths are resolved from the directory you run the command in.

## How it works, and where a person decides

```
exports (any number, any length)
  -> read, merge, drop duplicates
  -> identify vendors
  -> link pending charges to the posted charges that replaced them
  -> route each charge to its card's channel
  -> decide: draft / already-chased / skip / needs-routing
  -> fill the template for each charge being chased
  -> write: JSON, chase-list CSV, drafts for review
        ↓
  a person reviews the drafts and sends the ones they want   ← approval
        ↓
  pixi run sent  records what was sent in the chase log      ← approval
```

A person decides at each of these points; the Cog never decides for them:

1. **Sending.** Every draft is reviewed and sent by a person, or not sent at all.
2. **Recording what was sent.** A charge is marked chased only when a person runs `pixi run sent`.
   A draft that was thrown away comes back next run; one that was sent doesn't.
3. **Routing unknown cards.** A charge on a card that isn't in `cards.yaml` is drafted with no
   channel and marked `needs-routing`.
4. **Checking inferred matches.** When a posted charge is linked to a pending one by matching
   rather than by the export, the run warns and names it.
5. **Keeping the context current.** Cards, channels, users, the policy and the template are edited
   by people.

## Expected outputs

Three files in `--out` (default `./output/`), named after the period the exports cover, plus a
summary printed to the terminal:

- **`<name>.chase.json`**: every transaction in the shared shape, with this Cog's inferred keys:
  - `vendor`;
  - `route`: the card's channel;
  - `chase`: the decision and its reason;
  - `pending_match`, when a pending charge was matched rather than linked by the export.

  It also has the drafts, the superseded pending rows, and a run record: inputs, context versions,
  counts, warnings, and the model binding (`null`, no model yet). The contract is
  [`context/output-schema.json`](context/output-schema.json), with a short example in
  [`context/output-example.json`](context/output-example.json).
- **`<name>.chase-list.csv`**: one row per charge, in this order: needs routing, drafts, already
  chased, skipped.
- **`<name>.drafts.md`**: the drafts grouped by channel, ready to review and paste.

Chase decisions:

| Status | Means |
|---|---|
| `draft` | a message was drafted |
| `needs-routing` | a message was drafted, but the card has no channel; a person picks one |
| `already-chased` | this charge, or the pending charge it replaced, was sent before |
| `skip` | a refund, already coded by the auto-coder, or excluded by the policy |

## Completion criteria

- Every transaction across the exports appears once, with a decision and its reason.
- Every charge decided `draft` or `needs-routing` has exactly one draft.
- No charge recorded in the chase log is drafted again.
- Nothing is sent.

## Known limitations

- **Column names are a guess** until a real Brex export arrives.
- **The card list is invented.** Real cards, users and channels are needed before any draft is
  addressed correctly.
- **The policy chases almost everything.** Accounting hasn't said what counts as "enough
  information". Without the auto-coder's output, recurring subscriptions are chased too: 50 of 51
  charges in the sample month.
- **One message per charge.** A person with five charges gets five messages.
- **Matching pending to posted is a judgement.** It needs the same card, the same vendor (or the
  same start to the descriptor), and transaction dates at most 3 days apart. Two visits to the same
  place within 3 days on one card could be confused. Every match is flagged for checking.
- **The chase log is a local file.** Two people running the Cog with separate logs will chase the
  same charges.
- **Replies aren't read yet.** The reply form is there so they can be later.
- **No accuracy figures.** Evaluating whether the chase list matches what accounting would have
  chased needs a real month.
