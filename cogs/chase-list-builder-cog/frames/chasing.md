---
frame: chasing
version: "0.0.1"
status: draft
---

# Chasing card charges at OpenTeams

Org context for a model working on this Cog. It describes how accounting gets missing details about
card charges today. It is not a list of instructions; the cards, channels and policy are lookup data
in `context/`.

## Why chasing happens

The card is reconciled every month. Often the first accounting hears of a charge is when it appears
on the card. It's easy to pull out a card and pay, and the person spending doesn't think about what
accounting will need. A charge without details goes into a clearing account so the month can close,
and has to be moved later. The sooner the details arrive, the better: people remember a purchase
from Tuesday, not one from three weeks ago.

## What accounting needs for each charge

Vendor, amount and date come from the statement. What's missing is:

- what the purchase was;
- the department, and the class;
- the entity (always OpenTeams for this project);
- supporting documentation: a receipt or invoice.

More detail is better, especially at month end.

## Who to ask

- **OpenTeams has 10 Brex cards.** Each is used by a known set of people. Most people know
  everything on their own card.
- **Two cards are shared heavily,** mainly by engineering for software subscriptions, and for things
  like booking travel for others. The statement shows the name the card is under, not who used it.
- **The named cardholder is ultimately responsible** for the card's charges.
- **Today's order:** ask the person who uses the card most; if they don't know, widen out, usually
  copying in the named cardholder. Engineering charges are posted in an engineering card
  reconciliation Slack channel, where regular users, or whoever actually used the card, reply.
- **One channel per card** is the plan for this Cog: posting where the card's users are reaches
  whoever made the charge without guessing.

## How people respond

- Most people prefer Slack. Email is easier to search later. Either works for accounting.
- Requests are written out by hand each time today. When it isn't clear who to ask, they are
  broadcast, asking whether anyone knows anything about the charge.
- About half of recurring charges get their receipt forwarded without anyone asking. One-offs are
  the problem: **travel, and marketing purchases for events,** are the hardest to get details for.

## Placeholders, until accounting confirms

- The real cards, their users, and their channels.
- What counts as enough information: is a receipt plus a one-line description sufficient?
- Whether there is a deadline each month after which an unanswered charge goes to the clearing
  account.
