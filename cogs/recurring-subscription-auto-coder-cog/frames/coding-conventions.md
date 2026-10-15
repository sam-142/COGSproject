---
frame: coding-conventions
version: "0.0.1"
status: draft
---

# How OpenTeams codes card charges in QuickBooks

Org context for a model working on this Cog. The actual rules and the chart of accounts are lookup
data in `context/`; this explains what they mean and how accounting uses them.

## What goes in a QuickBooks entry

Accounting enters each card charge in QuickBooks with nine fields:

| Field | What it holds here |
|---|---|
| DATE | the transaction date |
| REF NO. | the last four digits of the card the charge was on |
| TYPE | credit card expense (or credit) |
| PAYEE | the vendor |
| ACCOUNT | the expense account, by its fully qualified name |
| MEMO | what the purchase was |
| CLASS | the line of business |
| DEPARTMENT | the team |
| CHARGE | the amount |

Brex already carries an expense account on every charge, which becomes ACCOUNT. It has no class or
department, and its memo is almost always empty, so those fields are often blank. Accounting also
wants to know **what the purchase is**; the vendor name gives a rough idea, but more detail is
better, especially at month end.

## Month end

The card is reconciled every month. A charge without enough information goes into a **clearing
account** so the month can close, and has to be moved to the right account later. An entry that is
right first time saves that adjustment. A wrong value costs more than a blank one, because nobody
looks at it again.

## How a recurring charge is usually entered

The same way as last month. A recurring charge's entry changes only when something about it
changes: it moves to another team, the vendor's product changes, or it starts being used by a
different line of business. A coding rule (vendor → payee, account, class, department) records the
way accounting enters a vendor, and overrides what Brex has.

## When an entry needs a second look

The entry is still written; these are flagged for a person to check:

- **A new vendor**, or one seen in only one earlier month.
- **An amount outside its usual range**: a price rise or added seats on a fixed-price vendor, or a
  big swing on a usage-billed one.

A pending charge gets no entry until it posts: the amount and descriptor can still change.

## Placeholders, until accounting confirms

- Whether the account on each Brex charge is one accounting chose, or one Brex filled in.
- Where class and department come from, if not Brex.
- The real chart of accounts, classes and departments.
- How software spend is split between accounts, for example hosting versus subscriptions.
