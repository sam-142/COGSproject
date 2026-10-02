---
frame: coding-conventions
version: "0.0.1"
status: draft
---

# How OpenTeams codes card charges in QuickBooks

Org context for a model working on this Cog. The actual rules and the chart of accounts are lookup
data in `context/`; this explains what they mean and how accounting uses them.

## What a coding is

Every card charge is entered into QuickBooks with:

- **an account** from the chart of accounts;
- **a class**, the line of business it belongs to;
- **a department**;
- **the entity** (company) it belongs to. For this Cog that is always OpenTeams.

Accounting also wants to know **what the purchase is**. The vendor name often gives a rough idea,
but more detail is better, especially at month end.

## Month end

The card is reconciled every month. A charge without enough information to code goes into a
**clearing account** so the month can close, and has to be moved to the right account later. A
coding that is proposed early and is right saves that adjustment. A coding that is wrong costs
more than leaving the charge uncoded, because nobody looks at it again.

## How a recurring charge is usually coded

The same way as last month. A recurring charge's coding changes only when something about it
changes: it moves to another team, the vendor's product changes, or it starts being used by a
different line of business. A coding rule therefore reflects the most recent month accounting
coded, not a general guess from the vendor type.

## When not to propose a coding

- **The charge is pending.** The amount and descriptor can still change.
- **Nothing ties the vendor to a coding:** no rule, and no history of how it was coded.
- **Something about the charge changed:** a new vendor, or an amount outside its usual range.

In each case, leaving it for a person is the expected outcome, not a failure.

## Placeholders, until accounting confirms

- The real chart of accounts, classes and departments (`context/chart-of-accounts.yaml` is
  synthetic).
- How software spend is split between accounts, for example hosting versus subscriptions.
- Which QuickBooks import format, if any, they would want instead of a review file.
