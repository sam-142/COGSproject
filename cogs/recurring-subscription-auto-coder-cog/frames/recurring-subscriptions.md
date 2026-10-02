---
frame: recurring-subscriptions
version: "0.0.1"
status: draft
---

# Recurring subscriptions on the OpenTeams Brex card

Org context for a model working on this Cog. It describes how recurring charges actually behave
here. It is not a list of instructions, and it is not the lookup data: vendor patterns and the
known recurring list are in `context/`.

## What the card looks like

- **Scope:** OpenTeams only, on 10 Brex cards. OSbig, Quansight and other entities are out of
  scope.
- **Volume:** 60–80 transactions a month. About three quarters are recurring software charges.
- **Shared cards:** two cards are shared heavily, mainly by engineering for software
  subscriptions, and new subscriptions get added to them. The name on a card is therefore not
  necessarily the person who set up a subscription on it.
- **Card numbers:** the PDF statement shows the cardholder's name but not the last four digits of
  the card. The online view shows both.
- **Brex's category** is a guess from the vendor name, and accounting doesn't use it. Don't treat
  `Software` as evidence that a charge is a subscription.

## How recurring charges behave

- **Most charge monthly at the same amount,** around the same day of the month.
- **Usage-billed services drift** month to month: cloud hosting, monitoring, messaging. A
  difference of a few percent is normal for them and doesn't mean anything changed.
- **Seat-based services change in steps** when people are added or removed. A second, smaller
  charge mid-month from a vendor already charging is usually a seat addition, not a new
  subscription.
- **One vendor can have several subscriptions.** Two charges from the same vendor in one month at
  different amounts may be two separate accounts, each recurring on its own.
- **Descriptors vary for the same vendor,** and change between pending and posted. Pending charges
  can show a placeholder amount or descriptor until they settle, two to four days later.
- **Annual subscriptions** appear once a year and look like one-offs unless someone has listed
  them.

## What isn't a subscription

Travel (flights, hotels, rides, transit), meals, event and marketing spend (booths, printing,
tickets), and marketplace purchases. Accounting says one-off travel and event marketing are the
hardest charges to get information about. They are handled by `chase-list-builder-cog`, not here.

## Documentation

Supporting documentation is the accounting standard. Receipts or invoices arrive for more than
half of recurring charges most months, often forwarded by whoever set up the subscription. Many
long-standing subscriptions never produce one. A missing receipt on a charge with a long history is
normal, and is not a reason to doubt that it's recurring.

## Placeholders, until accounting confirms

- Which subscriptions are annual, and when they renew.
- Which recurring charges are direct debits or standing orders.
- Whether a price change above some amount needs approval before it's coded.
