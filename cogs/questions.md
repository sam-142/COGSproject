# questions for the accounting team

**questions to be asked:**

**Question:** is there a way to export a set date (say last 5 days) of transactions into a csv file? if so, may we have a sample.
**Context:** this would make the receipt-parser much lighter weight, if we already got the data in csv format, we can hand it straight to the 2 main cogs, and have a much thinner skill, that checks the input data.


**questions answered already:**

**Question:** When it comes to the credit card reconciliation process, is the chasing people down for information and receipts still an issue?

**Answer:** Yes. Sometimes things get sent through and are entered without issue. But often the first anyone in accounting knows about a charge is when it appears on the card, and because a lot of cards get shared, it's not clear who actually made the charge. Finding information about what they are can eat up some time.

---

**Question:** Is that something you think would be worthwhile? Would it be valuable?

**Answer:** Not totally sure how it would work. Ideally, every time somebody made a charge on a card they would have to submit information to accounting. It's easy to pull out a card, enter a number and be on their way, and on the spender's end they don't think about it — but on the accounting end there's often no information to record things.

---

**Question:** How many different cardholders are there in the company, roughly?

**Answer:** It depends on the entity. Different cards exist for different entities — OpenTeams has about 10 cards out, OSbig has about 4, Quansight has a couple, and most accounts have a debit card. This project is specifically OpenTeams, so just the Brex cards: 10 in total.

---

**Question:** You have to enter all the transactions into QuickBooks, right?

**Answer:** Right.

---

**Question:** What exact information do you need from the cardholders to fill in all the necessary information?

**Answer:** Vendor name, amount, and date; what department the purchase is for; and some information about what the purchase is. The vendor can often be Googled to get an idea of what was bought, but the more details the better.

---

**Question:** When you reach out to them, is it through email or Slack?

**Answer:** Both, which has its own level of confusion. Most people seem to prefer Slack.

---

**Question:** Which would be ideal for you?

**Answer:** Slack gets used since people prefer it, but some things work better in email. Things are easier to find in email, and email is more familiar than Slack. Either one works.

---

**Question:** Is there policy behind chasing these people down — are there deadlines, or is it just out of goodwill?

**Answer:** The card has to be reconciled every month. Without the information, the transaction gets pushed into a clearing account so the month can be closed, and adjustments have to be made later to get the expense where it belongs. The sooner the information arrives, the better.

---

**Question:** How often does a wrong transaction show up that you have to flag?

**Answer:** Two or three a year. Not really an issue — those would be disputed anyway, and there's nothing really automatable about it. The real problem is incomplete information: not being able to record the company or entity, class and department, and information about what the purchase is. More detail is particularly valuable for the month-end process.

---

**Question:** Would you be able to provide any statements so we can get an idea of the data we'd be working with?

**Answer:** Yes, sharing was approved. The Brex statements are pretty complete and give everything accounting receives. (Separately: Chase statements arrive cut off — the PDF is letter-sized for a legal-length page, so the last dozen lines of every page are lost, and transactions have to be downloaded as Excel/CSV to get them all. This was set aside as a separate discussion.)

---

**Question:** Are the names consistent — is the employee on the card always the one using it?

**Answer:** Unfortunately no. Cards get shared a lot. The statement also does not include the last four of the card number, only the name the card is under; the last four is visible online and would be useful on the statement.

---

**Question:** Is the person whose name the card is under responsible for all the charges on that card?

**Answer:** Ultimately the buck stops with the named cardholder, but some cards are used by quite a few people because not everybody is issued a card. Examples: travel booked on someone else's card for Davos, and engineering using another card for software subscriptions — mostly one-offs, but some subscriptions have been added. Two cards in particular get used regularly by other people.

---

**Question:** But you're not going to know about every single charge all the time?

**Answer:** Correct. That responsibility has been delegated to certain individuals. Most people should know everything that's on their card — the widely shared ones are the exception.

---

**Question:** When there's a transaction you need more information on, how do you find who spent it? Do you use your own judgment?

**Answer:** It starts with the person known to use that card most, then works outward if they don't know, usually copying the named cardholder. There is an engineering credit card reconciliation Slack channel where the charge gets posted — the regular card users usually chime in, and often another engineer who actually used the card comes forward.

---

**Question:** Is the category/type reasonably accurate?

**Answer:** Not really. It's just Brex guessing based on who the vendor is. It doesn't get used.

---

**Question:** For recurring expenses, are those usually pretty consistently easy to resolve?

**Answer:** Most are, if they have history. Supporting documentation is the accounting standard and it's very helpful when whoever initiated the charge forwards it. But many long-standing ones come with nothing — receipts arrive for more than half most months, though there are quite a few that never produce anything.

---

**Question:** Would you be able to send us a copy of the statement? Is that something you're allowed to do?

**Answer:** Yes, with the most recent statement being the most useful. The caveat is to keep control of it — don't upload it into ChatGPT or out into the public cloud.

---

**Question:** When you reach out to people, do you have a template you copy and paste, or do you write it out?

**Answer:** It gets written out each time. A template would probably be pretty easy to have. Often it isn't clear who to ask, so the request gets broadcast — asking whether anybody knows anything about the charge and listing the pieces of information needed.

---

**Question:** Do a lot of people send information without being asked? What are the chances they haven't already emailed you?

**Answer:** Quite a few forward the invoice or receipt as they get it in their email — probably half of recurring charges, maybe a little more. For the rest nothing arrives, and it's unclear whether nobody receives anything or somebody receives it and doesn't know to forward it. Those tend to have history, so it's not too big a deal. The most problematic are travel, and marketing purchasing for events — one-offs. A suggested feature: letting people scan receipts on their phone as they travel, add the information as they go, and submit it all as a travel report at the end.

---

**Question:** Have there been any specific errors recently that you think we could help with?

**Answer:** None come to mind. OpenTeams typically has 60–80 transactions a month on the credit card, and about three quarters are repeating recurring software charges, making it much easier than the OSbig card. Only OpenTeams is in scope for now. The biggest challenge is that the accounting team knows its own processes but not what this project can actually do, so the most helpful next step is to bring proposals back and let the team say whether each is valuable — avoiding spending cycles on something unnecessary.