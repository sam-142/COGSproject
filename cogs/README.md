# COG implementation

**This is where the implementations for the cogs Chase-List Builder and Recurring subscription auto-coder live**,

---

each folder currently contains a COG.md file, a cog.yaml file, a skills folder, a frames folder, and a references folder. These COGS are to be build by referencing (but not bound by) the cogspec (SPEC.md) written by Trent Oliphant.

---

**Hurdles**

Here are some things I think it is worth keeping in mind during development:

**Pending transactions**

Card transactions appear pending with a provisional amount and a descriptor that often changes on settlement two to four days later. At a 3-day cadence we will see both states constantly. Proposed solution: chase on pending, code on posted. Chasing early is better because people remember what they bought on Tuesday, not three weeks ago, but never propose a QuickBooks coding off an amount that can still change. Most aggregators give you a link from the posted transaction back to its pending ID; if yours doesn't, match on card, merchant and date proximity and mark the link as inferred.

---

**Proposed Architecture:**

