"""Load and check the files in context/: cards, chase policy, message template,
and the shared vendor patterns.

Everything is checked once, at load, so a typo fails the run instead of
producing a message with a broken placeholder or a card routed nowhere.
"""
import string
from pathlib import Path

import yaml

from cog_transactions.vendors import compile_vendors

COG_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = COG_ROOT / "context"
TEMPLATE_NAME = "message-template.md"

# What a template may use. See context/README.md.
PLACEHOLDERS = {
    "card_last4", "cardholder", "channel", "merchant", "vendor", "amount", "currency",
    "original_amount", "date", "status", "status_note", "questions", "reply_form",
    "transaction_id",
}


class ContextError(ValueError):
    pass


def _yaml(directory, name):
    path = Path(directory) / f"{name}.yaml"
    if not path.exists():
        raise ContextError(f"missing context file {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_template(path):
    path = Path(path)
    if not path.exists():
        raise ContextError(f"missing message template {path}")
    text = path.read_text(encoding="utf-8")
    try:
        used = {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}
    except ValueError as e:
        raise ContextError(f"{path.name}: {e} (write {{{{ or }}}} for a literal brace)") from e
    unknown = used - PLACEHOLDERS
    if unknown:
        raise ContextError(f"{path.name}: unknown placeholder(s) {', '.join(sorted(unknown))}; "
                           f"allowed: {', '.join(sorted(PLACEHOLDERS))}")
    return text


def load(directory=DEFAULT_DIR, template_path=None):
    raw = {name: _yaml(directory, name) for name in ("vendors", "cards", "chase-policy")}

    try:
        vendors = compile_vendors(raw["vendors"].get("vendors", []))
    except ValueError as e:
        raise ContextError(f"vendors: {e}") from e

    cards = {}
    for c in raw["cards"].get("cards", []):
        last4 = str(c["last4"])
        if last4 in cards:
            raise ContextError(f"cards: {last4} listed twice")
        cards[last4] = {"cardholder": c.get("cardholder"), "channel": c.get("channel"),
                        "users": list(c.get("users") or []), "shared": bool(c.get("shared"))}

    policy = raw["chase-policy"]
    ask_for = policy.get("ask_for") or []
    if not ask_for:
        raise ContextError("chase-policy: ask_for is empty, so messages would ask nothing")
    for item in ask_for:
        if item.get("skip_if") not in (None, "receipt_attached"):
            raise ContextError(f"chase-policy: unknown skip_if {item['skip_if']!r}")

    template_path = Path(template_path) if template_path else Path(directory) / TEMPLATE_NAME
    return {
        "vendors": vendors,
        "cards": cards,
        "policy": {
            "skip_refunds": bool(policy.get("skip_refunds", True)),
            "skip_coded_by_auto_coder": bool(policy.get("skip_coded_by_auto_coder", True)),
            "skip_when_receipt_and_memo": bool(policy.get("skip_when_receipt_and_memo", False)),
            "ask_for": ask_for,
        },
        "template": load_template(template_path),
        "template_file": template_path.name,
        "versions": {name: {"version": str(raw[name].get("version")),
                            "status": raw[name].get("status", "unspecified")}
                     for name in raw},
    }
