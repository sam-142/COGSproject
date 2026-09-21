# COGSproject

This document outlines the plan for the following COGS development:

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

Since both Cogs must be able to parse the transactions, it makes the most sense to start by making a cog that can do just that.

This includes:
- Drafting up a barebones cog.md, and cog.yaml file
- Implementing a script that actually parses the transaction details
- For missing/misleading information that Ruth talked about, implement an inference model (Qwen 3, or another
  open-scource model), that can reason about these gaps in knowledge.
- Explore the use of Frames (mainly the ones Reed has already written), for context the model can draw from.

Testing:
- Test against a specific data set (Openteams past bank statements)
- Report success rate, anomalies, etc

This Cog would serve as the base for both of the above Cogs, we just need to build upon it to serve the 2 different purposes

**For the Recurring Subscription auto-coder, this could include:**
- Relevant additions to cog.md and cog.yaml.
- A separate frame, outlining the decision process to identify monthly payments.
- A list, of already existing direct debits/standing orders (if known by the accounting team)
- A separate script, with model integration, that filters through the output of the other script, to produce a list 
  of recurring subscriptions.

---

**For the Chase-list builder:**

At the most basic level:
- Relevant additions to cog.md and cog.yaml
- For each transaction that isnt a monthly subscription, identify the cardholder name, draft a message including the
  transaction details, and send this message to the cardholder slack channel. Request a structured response.
- Using the structured response, use a script to parse, and append this information onto the old transaction details.

More complex needs:

Receipt parsing:
- Functionality to parse both physical and digital receipts
- We will most likely have to lean heavily on the model to do this, as most digital receipts look vastly different.

