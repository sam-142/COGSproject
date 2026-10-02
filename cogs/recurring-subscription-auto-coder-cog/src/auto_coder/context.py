"""Load and check the lookup files in context/.

These are structured data the code reads directly: vendor patterns, the known
recurring list, coding rules and the chart of accounts. (The Markdown files in
frames/ are different: they are org context written for a model to read.)

The files are checked against each other here, once, so a typo in a rule fails
at load time instead of turning into a quietly wrong coding.
"""
from pathlib import Path

import yaml

from cog_transactions.vendors import compile_vendors

COG_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = COG_ROOT / "context"
FILES = ("vendors", "known-recurring", "coding-rules", "chart-of-accounts")


class ContextError(ValueError):
    pass


def _read(directory, name):
    path = Path(directory) / f"{name}.yaml"
    if not path.exists():
        raise ContextError(f"missing context file {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load(directory=DEFAULT_DIR):
    raw = {name: _read(directory, name) for name in FILES}

    try:
        vendors = compile_vendors(raw["vendors"].get("vendors", []))
    except ValueError as e:
        raise ContextError(f"vendors: {e}") from e
    known_ids = {v["id"] for v in vendors}

    chart = raw["chart-of-accounts"]
    allowed = {
        "account": {str(a["number"]) for a in chart.get("accounts", [])},
        "class": set(chart.get("classes", [])),
        "department": set(chart.get("departments", [])),
        "entity": set(chart.get("entities", [])),
    }

    rules = {}
    for r in raw["coding-rules"].get("rules", []):
        vid = str(r["vendor"])
        if vid not in known_ids:
            raise ContextError(f"coding-rules: unknown vendor {vid}")
        rule = {k: str(r[k]) for k in allowed}
        for field, value in rule.items():
            if value not in allowed[field]:
                raise ContextError(f"coding-rules: {vid} uses {field} {value!r}, not in chart-of-accounts")
        rules[vid] = rule

    known = {}
    for k in raw["known-recurring"].get("recurring", []):
        vid = str(k["vendor"])
        if vid not in known_ids:
            raise ContextError(f"known-recurring: unknown vendor {vid}")
        known[vid] = {"cadence": k.get("cadence", "monthly"), "amount": k.get("amount")}

    return {
        "vendors": vendors,
        "rules": rules,
        "known_recurring": known,
        # Recorded on every run, so a result says which version of the org
        # knowledge produced it, and whether that knowledge was real.
        "versions": {name: {"version": str(raw[name].get("version")),
                            "status": raw[name].get("status", "unspecified")}
                     for name in FILES},
    }
