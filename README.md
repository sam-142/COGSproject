# COGSproject

This document outlines the plan for the following COGS development:

All cogs should be pixi packages.

**Recurring Subscription Auto-coder:**

Needs to:
- Be able to identify monthly recurring transactions
- Parse the transaction, and structure the information in a way that streamlines QuickBooks process

---

**Chase-list builder:**

Needs to:
- Be able to Parse the transactions into a structured format.
- Identify missing information
- Draft an outreach message outlining necessary information.
- Parse responses, append the new information to the parsed transaction, and structure the information in a way that
  streamlines QuickBooks Process.

---

**Proposed development timeline:**

The two Cogs are built independently. A shared transaction-parsing Cog was considered and dropped:
building a whole separate Cog for two consumers would be a waste of time. Each Cog reads the
statements itself, with a thin parsing step that gives both the same transaction structure. If the
accounting team can export transactions as CSV (see `cogs/questions.md`), that step gets even
thinner.

**Common to both Cogs:**
- Drafting up a barebones COG.md, and cog.yaml file
- A thin script that reads the transaction details from the statement (or CSV export)
- For missing/misleading information that Ruth talked about, implement an inference model (Qwen 3, or another
  open-scource model), that can reason about these gaps in knowledge.
- Explore the use of Frames (mainly the ones Reed has already written), for context the model can draw from.

**Testing:**
- Test against a specific data set (Openteams past bank statements)
- Report success rate, anomalies, etc

---

**For the Recurring Subscription auto-coder, this could include:**
- Relevant additions to COG.md and cog.yaml.
- A separate frame, outlining the decision process to identify monthly payments.
- A list, of already existing direct debits/standing orders (if known by the accounting team)
- A separate script, with model integration, that filters through the parsed transactions, to produce a list 
  of recurring subscriptions.

---

**For the Chase-list builder:**

At the most basic level:
- Relevant additions to COG.md and cog.yaml
- For each transaction that isnt a monthly subscription, identify the cardholder name, draft a message including the
  transaction details, and send this message to the cardholder slack channel. Request a structured response.
- Using the structured response, use a script to parse, and append this information onto the old transaction details.

More complex needs:

Receipt parsing:
- Functionality to parse both physical and digital receipts
- We will most likely have to lean heavily on the model to do this, as most digital receipts look vastly different.

