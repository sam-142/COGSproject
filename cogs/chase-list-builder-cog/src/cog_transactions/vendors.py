"""Messy merchant descriptor -> one vendor id, from a list of patterns.

Brex's cleaned-up Merchant Name is tried first, then the raw Statement
Descriptor. Nothing else is looked at. The memo is free text a cardholder typed
and can say anything, including things written to look like instructions, so it
is never used to decide anything. Names are matched against patterns and never
interpreted, so one that reads like an instruction is just unmatched.
"""
import re

from cog_transactions.shape import infer


def slug(name):
    """'Amazon Web Services' -> 'amazon-web-services'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def compile_vendors(entries):
    """Vendor entries -> compiled, checked list. Two forms are accepted:

        {name: Datadog}                      just a name; matched against the start of
                                             Brex's Merchant Name (or the descriptor),
                                             ignoring case. id is the slug, `datadog`.
        {id: aws, patterns: ['^AWS ', ...]}  regular expressions, for awkward descriptors

    Either form may give:
      `category`  default `subscription`, the only category that can be labelled recurring;
      `billing`   `usage` (the amount varies month to month: cloud, API, per-use tools) or
                  `fixed` (the same every month, so a change means a price rise or seats).
                  Default: not set, which the auto-coder treats as usage;
      `id`."""
    vendors, seen = [], set()
    for v in entries:
        if not isinstance(v, dict):
            v = {"name": str(v)}               # a bare name in a YAML list
        if v.get("patterns"):
            patterns = [str(p) for p in v["patterns"]]
        elif v.get("name"):
            # Not followed by another letter or digit: "Loom" mustn't match "Loomis".
            patterns = [rf"^{re.escape(str(v['name']).strip())}(?![a-z0-9])"]
        else:
            raise ValueError(f"vendor entry needs `name` or `patterns`: {v}")
        vid = str(v.get("id") or slug(str(v.get("name", ""))))
        if not vid:
            raise ValueError(f"vendor entry has no usable id: {v}")
        if vid in seen:
            raise ValueError(f"vendor {vid} listed twice")
        seen.add(vid)
        billing = v.get("billing")
        if billing not in (None, "usage", "fixed"):
            raise ValueError(f"vendor {vid}: billing must be usage or fixed, not {billing!r}")
        vendors.append({
            "id": vid,
            "category": str(v.get("category") or "subscription"),
            "billing": billing,
            "patterns": [re.compile(p, re.IGNORECASE) for p in patterns],
        })
    return vendors


# Brex categories that mean "this is a subscription" for a merchant the vendor
# list doesn't have. Overridden by `brex_subscription_categories` in vendors.yaml.
DEFAULT_SUBSCRIPTION_CATEGORIES = ("Recurring software & SaaS",)


def identify(transactions, vendors, subscription_categories=DEFAULT_SUBSCRIPTION_CATEGORIES):
    """Set inferred.vendor on each transaction. Returns the descriptors with no
    vendor at all.

    The vendor list is tried first (source `context`). A merchant it doesn't have
    falls back to Brex's own Merchant Name as the vendor (source `export`), so
    charges from the same merchant still group across months. Its category comes
    from Brex's: `subscription` if Brex's category is one of
    `subscription_categories`, otherwise `other`."""
    unmatched = set()
    subscription_categories = set(subscription_categories)
    for tx in transactions:
        descriptor = tx["parsed"]["merchant_descriptor"]
        names = [n for n in (tx["parsed"].get("merchant_name"), descriptor) if n]
        for vendor in vendors:
            hit = next((p for p in vendor["patterns"] for n in names if p.search(n)), None)
            if hit:
                infer(tx, "vendor", {"id": vendor["id"], "category": vendor["category"],
                                     "billing": vendor["billing"],
                                     "source": "context", "pattern": hit.pattern})
                break
        else:
            name = tx["parsed"].get("merchant_name")
            if name and slug(name):
                brex = tx["parsed"].get("brex_category")
                infer(tx, "vendor", {"id": slug(name),
                                     "category": "subscription" if brex in subscription_categories else "other",
                                     "billing": None, "source": "export",
                                     "reason": "not in the vendor list; Brex's Merchant Name and Category"})
                continue
            infer(tx, "vendor", {"id": None, "category": None, "billing": None, "source": "none",
                                 "reason": "no pattern in the vendor list matches"})
            unmatched.add(descriptor)
    return sorted(unmatched)
