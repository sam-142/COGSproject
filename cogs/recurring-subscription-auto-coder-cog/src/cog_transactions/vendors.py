"""Messy merchant descriptor -> one vendor id, from a list of patterns.

Only the descriptor is looked at. The memo is free text a cardholder typed and
can say anything, including things written to look like instructions, so it is
never used to decide anything. A descriptor is matched against patterns and
never interpreted, so one that reads like an instruction is just unmatched.
"""
import re

from cog_transactions.shape import infer


def compile_vendors(entries):
    """[{id, category, patterns: [regex, ...]}, ...] -> compiled, checked list."""
    vendors, seen = [], set()
    for v in entries:
        vid = str(v["id"])
        if vid in seen:
            raise ValueError(f"vendor {vid} listed twice")
        seen.add(vid)
        vendors.append({
            "id": vid,
            "category": v["category"],
            "patterns": [re.compile(p, re.IGNORECASE) for p in v["patterns"]],
        })
    return vendors


def identify(transactions, vendors):
    """Set inferred.vendor on each transaction. Returns the unmatched descriptors."""
    unmatched = set()
    for tx in transactions:
        descriptor = tx["parsed"]["merchant_descriptor"]
        for vendor in vendors:
            hit = next((p for p in vendor["patterns"] if p.search(descriptor)), None)
            if hit:
                infer(tx, "vendor", {"id": vendor["id"], "category": vendor["category"],
                                     "source": "context", "pattern": hit.pattern})
                break
        else:
            infer(tx, "vendor", {"id": None, "category": None, "source": "none",
                                 "reason": "no pattern in the vendor list matches"})
            unmatched.add(descriptor)
    return sorted(unmatched)
