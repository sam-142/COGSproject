"""The transaction shape both Cogs share, and the code that produces it.

SHARED WITH chase-list-builder-cog. That Cog gets this package by copying it,
not by depending on this one: copy this directory and
context/transaction.schema.json across unchanged, and never edit only one copy.
Anything specific to one Cog (recurrence, coding, chasing) does not belong here.

A transaction is:

    {
      "id":       the export's transaction id,
      "source":   {"file": ..., "row": ...}   where it was read from,
      "parsed":   values read straight from the export, nothing else,
      "inferred": everything worked out afterwards, one object per key,
                  each carrying a "source" saying where it came from
    }

A field name may appear in `parsed` or `inferred`, never both. That is checked
by the schema, not left to convention, so an inferred value can't be passed off
as one read from the statement.
"""

SHAPE_VERSION = "0.1.0"
