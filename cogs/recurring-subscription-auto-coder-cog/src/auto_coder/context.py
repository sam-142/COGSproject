"""Load and check the lookup files in context/.

These are structured data the code reads directly: vendor patterns, the known
recurring list, coding rules and the chart of accounts. (The Markdown files in
frames/ are different: they are org context written for a model to read.)

The files are checked against each other here, once, so a typo in a rule fails
at load time instead of turning into a quietly wrong coding.
"""
from pathlib import Path

import yaml

from cog_transactions.vendors import DEFAULT_SUBSCRIPTION_CATEGORIES, compile_vendors

COG_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = COG_ROOT / "context"
FILES = ("vendors", "known-recurring", "coding-rules", "chart-of-accounts", "quickbooks")

# QuickBooks entry settings, used when quickbooks.yaml leaves one out.
QB_DEFAULTS = {"type_charge": "Credit Card Expense", "type_credit": "Credit Card Credit",
               "date_format": "%m/%d/%Y", "ref_field": "card_last4", "ref_max_length": None}
RULE_FIELDS = ("payee", "account", "class", "department")


class ContextError(ValueError):
    pass


def check_override_dir(override_dir, names):
    """Fail loudly instead of silently falling back to the defaults."""
    if override_dir is None:
        return
    d = Path(override_dir)
    if d.is_file():
        raise ContextError(f"--context takes a folder, not a file: use --context {d.parent}")
    if not d.is_dir():
        raise ContextError(f"--context folder not found: {d}")
    if not any((d / n).exists() for n in names):
        raise ContextError(f"--context folder {d} has none of: {', '.join(names)}")


def _read(path):
    if not path.exists():
        raise ContextError(f"missing context file {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load(override_dir=None):
    """Read the four lookup files. A file in `override_dir` replaces this Cog's
    default; any file it doesn't have keeps the default. That lets real data
    (a vendor list, coding rules) live outside the repo, in private/, one file
    at a time."""
    check_override_dir(override_dir, [f"{n}.yaml" for n in FILES])
    sources = {}
    for name in FILES:
        own = Path(override_dir) / f"{name}.yaml" if override_dir else None
        sources[name] = own if own and own.exists() else DEFAULT_DIR / f"{name}.yaml"
    raw = {name: _read(path) for name, path in sources.items()}
    warnings = []

    try:
        vendors = compile_vendors(raw["vendors"].get("vendors", []))
    except ValueError as e:
        raise ContextError(f"vendors: {e}") from e

    chart = raw["chart-of-accounts"]
    allowed = {
        "account": {str(a["number"]) for a in chart.get("accounts", [])},
        "class": set(chart.get("classes", [])),
        "department": set(chart.get("departments", [])),
        "entity": set(chart.get("entities", [])),
    }

    # Rules and known-recurring entries apply by vendor id, whether the id comes
    # from the vendor list or from Brex's Merchant Name (`datadog` for "Datadog"),
    # so an entry for a vendor not on the list is kept, not rejected.
    rules = {}
    for r in raw["coding-rules"].get("rules", []):
        vid = str(r["vendor"])
        rule = {k: str(r[k]) for k in RULE_FIELDS if r.get(k) not in (None, "")}
        for field in ("account", "class", "department"):
            # An empty list in the chart means it wasn't supplied: nothing to check against.
            if field in rule and allowed[field] and rule[field] not in allowed[field]:
                raise ContextError(f"coding-rules: {vid} uses {field} {rule[field]!r}, not in chart-of-accounts")
        rules[vid] = rule

    known = {}
    for k in raw["known-recurring"].get("recurring", []):
        known[str(k["vendor"])] = {"cadence": k.get("cadence", "monthly"), "amount": k.get("amount")}

    qb = {**QB_DEFAULTS, **{k: v for k, v in (raw["quickbooks"] or {}).items() if k in QB_DEFAULTS}}
    if qb["ref_field"] not in ("card_last4", "reference_id", "transaction_id"):
        raise ContextError("quickbooks: ref_field must be card_last4, reference_id or transaction_id, "
                           f"not {qb['ref_field']!r}")

    return {
        "vendors": vendors,
        "rules": rules,
        "known_recurring": known,
        "quickbooks": qb,
        "subscription_categories": tuple(raw["vendors"].get("brex_subscription_categories")
                                         or DEFAULT_SUBSCRIPTION_CATEGORIES),
        # Recorded on every run, so a result says which version of the org
        # knowledge produced it, and whether that knowledge was real.
        "versions": {name: {"version": str(raw[name].get("version")),
                            "status": raw[name].get("status", "unspecified"),
                            "from": "override" if sources[name].parent != DEFAULT_DIR else "default"}
                     for name in FILES},
        "warnings": warnings,
    }
