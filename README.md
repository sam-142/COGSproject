# COGSproject

Two Cogs that take the routine work out of OpenTeams' Brex card reconciliation. Both are pixi
packages, built to Trent Oliphant's CogSpec v0.1 (`cogs/SPEC.md`).

| Cog | What it does today |
|---|---|
| **Recurring subscription auto-coder** (`cogs/recurring-subscription-auto-coder-cog/`) | Finds the recurring subscription charges in a month's Brex statement and fills in their memo, the way accounting's OT Vendor Subscription List does, giving back **the statement ready to upload to QuickBooks** plus a report of what to check. |
| **Chase-list builder** (`cogs/chase-list-builder-cog/`) | Finds the charges accounting needs details on and drafts a message for each, addressed to the card's channel, for a person to review and send. It never sends anything |

Both read **Brex's standard CSV export** (all 70 columns, as downloaded) and keep only the 22 columns
they use. Neither uses a model yet: every step is deterministic, and the model is deliberately
left until last.

## Where things are

| Path | What |
|---|---|
| `cogs/` | the two Cogs, the spec, and accounting's answers so far (`questions.md`). `cogs/README.md` describes how each Cog is built |
| `sample-data/` | synthetic test data in Brex's real layout, one folder per test case, plus the invented context the tests use |
| `app/` | the web page for the accounting team, over both Cogs. Contains no Cog code: it runs each Cog through its pixi tasks |
| `tools/` | scripts you run yourself on real data: `profile_export.py` (shape-only summary of an export) and `vendors_to_yaml.py` (vendor list to YAML) |
| `private/` | **real exports and real context files.** Gitignored, and blocked from Claude |
| `ROADMAP.md` | what's done and what's left |
| `CLAUDE.md` | rules and conventions for working in this repo |

## For the accounting team: the app

A small web page runs both Cogs in one go. It runs on your own computer only and loads nothing from
the internet, so statements never leave the machine. It lives in `app/`, outside both Cogs.

1. Open a terminal in this folder and start it:
   ```bash
   pixi run --manifest-path app/pixi.toml ui --context private/context --log private/chase-log.json
   ```
   The page opens in your browser. (Leave out `--context …` or `--log …` if those don't exist yet.)
2. Drop **this month's Brex statement** in the first box, and **earlier months' statements** in the
   second (two or more let charges be confirmed as recurring).
3. Press **Run**.
4. Download **the updated statement** (upload this to QuickBooks) and **the review report**. Below
   them is **a Slack draft for every other charge still without a memo**, grouped by channel, each
   with a Copy button. Nothing is sent.
5. Press **Ctrl+C** in the terminal when you're done. Everything you uploaded, and every result, is
   deleted when it stops; save the downloads first.

More in `app/README.md`.

## Running on real data (command line)

Real exports, real context files and the outputs all stay in `private/`. From the repo root:

```bash
# auto-coder: the month to code, plus earlier months as history
pixi run --manifest-path cogs/recurring-subscription-auto-coder-cog/pixi.toml \
  code private/brex-2026-09.csv --history private/brex-2026-07.csv private/brex-2026-08.csv \
  --context private/context --out private/output

# chase-list builder: on the auto-coder's updated statement, so only charges with no memo are chased
pixi run --manifest-path cogs/chase-list-builder-cog/pixi.toml \
  draft private/output/brex-2026-09.upload.csv \
  --context private/context --log private/chase-log.json --out private/output
```

`--context` is a folder of real context files (vendor list, coding rules, cards and channels…) that
replace the Cogs' empty defaults one file at a time. `tools/vendors_to_yaml.py` turns a plain vendor
list into the `vendors.yaml` it expects.

**Real data never passes through Claude.** Claude runs in Anthropic's cloud, and accounting's rule
is that statements don't go to the public cloud. Run the Cogs and tools yourself, read the outputs
yourself, and describe problems in general terms. See `CLAUDE.md`.

## Original brief

**Recurring subscription auto-coder:** identify monthly recurring transactions, and structure them
for QuickBooks. *Done for posted charges; the QuickBooks file is in accounting's exact fields.*

**Chase-list builder:** parse the transactions, identify missing information, draft an outreach
message, then parse the responses and add the answers to the transaction. *Done up to drafting;
reading replies back in is next.*

**Receipt parsing** (physical and digital receipts) is not started, and whether it belongs in the
chase-list builder or its own Cog is still open.

Status, and everything left to do, is in `ROADMAP.md`.
